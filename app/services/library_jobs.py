from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.archive.identity import compute_archive_id, compute_full_sha256, compute_partial_sha1
from app.archive.reader import get_reader
from app.archive.types import is_supported_archive
from app.core.config import get_settings
from app.image.thumbnails import generate_thumbnail, get_image_size
from app.models import Archive, ArchivePage, BackgroundJob, FileDuplicateGroup, FileDuplicateMember
from app.services.background_jobs import append_job_log, finish_job, should_stop, start_job


def scan_library_job(db: Session, job: BackgroundJob) -> dict:
    settings = get_settings()
    paths = _archive_paths(settings.archive_dir)
    start_job(job, len(paths))
    append_job_log(job, f"Scanning {settings.archive_dir}")
    db.commit()

    for path in paths:
        if should_stop(db, job):
            append_job_log(job, "Scan stopped by user.")
            finish_job(job, "canceled")
            db.commit()
            return _job_result(job)

        job.current_item = str(path)
        try:
            archive_id = compute_archive_id(path)
            existing = db.get(Archive, archive_id)
            if existing:
                existing.partial_hash = existing.partial_hash or archive_id
                job.skipped_items += 1
                append_job_log(job, f"Skipped existing archive: {path.name}")
                db.commit()
                continue

            stat = path.stat()
            archive = Archive(
                id=archive_id,
                title=path.stem,
                filename=path.name,
                file_path=str(path),
                extension=path.suffix.lower().lstrip("."),
                file_size=stat.st_size,
                file_mtime=datetime.fromtimestamp(stat.st_mtime, timezone.utc),
                partial_hash=archive_id,
            )
            db.add(archive)
            db.flush()
            _index_archive_pages(db, archive)
            job.completed_items += 1
            append_job_log(job, f"Imported {path.name}")
        except Exception as exc:  # noqa: BLE001 - keep scanning remaining files
            job.failed_items += 1
            job.error = str(exc)
            append_job_log(job, f"Failed {path}: {exc}")
        finally:
            db.commit()

    finish_job(job, "failed" if job.failed_items else "completed")
    db.commit()
    return _job_result(job)


def generate_thumbnails_job(db: Session, job: BackgroundJob) -> dict:
    settings = get_settings()
    archives = list(db.scalars(select(Archive).order_by(Archive.title)))
    start_job(job, len(archives))
    append_job_log(job, f"Generating cover thumbnails for {len(archives)} archive(s).")
    db.commit()

    for archive in archives:
        if should_stop(db, job):
            append_job_log(job, "Thumbnail generation stopped by user.")
            finish_job(job, "canceled")
            db.commit()
            return _job_result(job)

        job.current_item = archive.filename
        try:
            _generate_archive_cover(settings, archive)
            job.completed_items += 1
            append_job_log(job, f"Generated cover: {archive.filename}")
        except Exception as exc:  # noqa: BLE001 - keep processing remaining archives
            job.failed_items += 1
            job.error = str(exc)
            append_job_log(job, f"Failed {archive.filename}: {exc}")
        finally:
            db.commit()

    finish_job(job, "failed" if job.failed_items else "completed")
    db.commit()
    return _job_result(job)


def check_file_duplicates_job(db: Session, job: BackgroundJob) -> dict:
    settings = get_settings()
    paths = _archive_paths(settings.archive_dir)
    start_job(job, len(paths))
    append_job_log(job, "Checking duplicates with file_size -> partial_sha1 -> full_sha256.")
    db.execute(delete(FileDuplicateMember))
    db.execute(delete(FileDuplicateGroup))
    db.commit()

    by_size: dict[int, list[Path]] = defaultdict(list)
    for path in paths:
        try:
            by_size[path.stat().st_size].append(path)
        except OSError as exc:
            job.failed_items += 1
            append_job_log(job, f"Cannot stat {path}: {exc}")
            db.commit()

    partial_candidates: dict[tuple[int, str], list[Path]] = defaultdict(list)
    for file_size, size_group in by_size.items():
        if len(size_group) < 2:
            job.skipped_items += len(size_group)
            continue

        for path in size_group:
            if should_stop(db, job):
                append_job_log(job, "Duplicate check stopped by user.")
                finish_job(job, "canceled")
                db.commit()
                return _job_result(job)

            job.current_item = str(path)
            try:
                partial_hash = compute_partial_sha1(path)
                _update_archive_hashes(db, path, partial_hash=partial_hash)
                partial_candidates[(file_size, partial_hash)].append(path)
            except Exception as exc:  # noqa: BLE001
                job.failed_items += 1
                job.error = str(exc)
                append_job_log(job, f"Partial hash failed {path}: {exc}")
            finally:
                db.commit()

    full_candidates: dict[tuple[int, str, str], list[Path]] = defaultdict(list)
    for (file_size, partial_hash), partial_group in partial_candidates.items():
        if len(partial_group) < 2:
            job.skipped_items += len(partial_group)
            db.commit()
            continue

        for path in partial_group:
            if should_stop(db, job):
                append_job_log(job, "Duplicate check stopped by user.")
                finish_job(job, "canceled")
                db.commit()
                return _job_result(job)

            job.current_item = str(path)
            try:
                full_sha256 = compute_full_sha256(path)
                _update_archive_hashes(db, path, partial_hash=partial_hash, full_sha256=full_sha256)
                full_candidates[(file_size, partial_hash, full_sha256)].append(path)
                job.completed_items += 1
            except Exception as exc:  # noqa: BLE001
                job.failed_items += 1
                job.error = str(exc)
                append_job_log(job, f"Full hash failed {path}: {exc}")
            finally:
                db.commit()

    group_count = 0
    for (file_size, partial_hash, full_sha256), full_group in full_candidates.items():
        if len(full_group) < 2:
            continue
        duplicate_group = FileDuplicateGroup(
            file_size=file_size,
            partial_hash=partial_hash,
            full_sha256=full_sha256,
            member_count=len(full_group),
        )
        db.add(duplicate_group)
        db.flush()
        for path in full_group:
            archive = db.scalar(select(Archive).where(Archive.file_path == str(path)))
            db.add(
                FileDuplicateMember(
                    group=duplicate_group,
                    archive_id=archive.id if archive else None,
                    file_path=str(path),
                    filename=path.name,
                    file_size=file_size,
                )
            )
        group_count += 1

    append_job_log(job, f"Found {group_count} duplicate group(s).")
    finish_job(job, "failed" if job.failed_items else "completed")
    db.commit()
    return {**_job_result(job), "duplicate_groups": group_count}


def _archive_paths(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file() and is_supported_archive(path))


def _index_archive_pages(db: Session, archive: Archive) -> None:
    reader = get_reader(archive.file_path)
    image_paths = reader.list_images()
    archive.pages.clear()

    for index, inner_path in enumerate(image_paths, start=1):
        width = height = byte_size = None
        if index == 1:
            first_page = reader.read_file(inner_path)
            width, height = get_image_size(first_page)
            byte_size = len(first_page)
            _generate_archive_cover(get_settings(), archive, first_page)

        archive.pages.append(
            ArchivePage(page_index=index, inner_path=inner_path, width=width, height=height, byte_size=byte_size)
        )

    archive.page_count = len(image_paths)


def _generate_archive_cover(settings, archive: Archive, first_page: bytes | None = None) -> None:
    reader = get_reader(archive.file_path)
    if first_page is None:
        image_paths = reader.list_images()
        if not image_paths:
            raise ValueError("Archive has no image pages.")
        first_page = reader.read_file(image_paths[0])

    thumbnail_format = normalize_thumbnail_format(settings.thumbnail_format)
    thumb_path = settings.thumb_dir / archive.id[:2] / f"{archive.id}.{thumbnail_format}"
    archive.cover_hash = generate_thumbnail(first_page, thumb_path, output_format=thumbnail_format)
    archive.cover_path = str(thumb_path)


def normalize_thumbnail_format(value: str) -> str:
    value = (value or "webp").lower().lstrip(".")
    if value == "jpeg":
        return "jpg"
    if value in {"webp", "jxl", "jpg"}:
        return value
    return "webp"


def _update_archive_hashes(
    db: Session,
    path: Path,
    partial_hash: str | None = None,
    full_sha256: str | None = None,
) -> None:
    archive = db.scalar(select(Archive).where(Archive.file_path == str(path)))
    if not archive:
        return
    if partial_hash:
        archive.partial_hash = partial_hash
    if full_sha256:
        archive.full_sha256 = full_sha256


def _job_result(job: BackgroundJob) -> dict:
    return {
        "success": job.status == "completed",
        "status": job.status,
        "completed": job.completed_items,
        "skipped": job.skipped_items,
        "failed": job.failed_items,
    }
