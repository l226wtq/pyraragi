from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.archive.identity import compute_archive_id, compute_full_sha256, compute_partial_sha1, md5_bytes, sha256_bytes
from app.archive.reader import get_reader
from app.archive.types import is_supported_archive
from app.core.config import get_settings
from app.image.fingerprints import compute_dhash, hash_bands, hash_distance
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


def scan_page_fingerprints_job(db: Session, job: BackgroundJob) -> dict:
    settings = get_settings()
    archives = list(db.scalars(select(Archive).order_by(Archive.title)))
    total_pages = sum(archive.page_count for archive in archives)
    start_job(job, total_pages)
    append_job_log(
        job,
        f"Scanning page fingerprints for {len(archives)} archive(s), perceptual threshold={settings.perceptual_hash_distance_threshold}.",
    )
    db.commit()

    seen: dict[str, tuple[str, int]] = {}
    dhash_index: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
    duplicate_count = 0
    similar_count = 0

    for archive in archives:
        if not archive.pages:
            _index_archive_pages(db, archive)
            db.commit()

        reader = get_reader(archive.file_path)
        for page in archive.pages:
            if should_stop(db, job):
                append_job_log(job, "Page fingerprint scan stopped by user.")
                finish_job(job, "canceled")
                db.commit()
                return {**_job_result(job), "duplicates": duplicate_count, "similar": similar_count}

            job.current_item = f"{archive.filename} page {page.page_index}"
            try:
                content = reader.read_file(page.inner_path)
                page.content_md5 = md5_bytes(content)
                page.content_sha256 = sha256_bytes(content)
                page.content_dhash = compute_dhash(content)
                page.byte_size = len(content)
                if page.width is None or page.height is None:
                    page.width, page.height = get_image_size(content)

                first_seen = seen.get(page.content_md5)
                if first_seen:
                    page.page_type = "duplicate"
                    page.hidden = True
                    page.duplicate_of_archive_id = first_seen[0]
                    page.duplicate_of_page_index = first_seen[1]
                    page.dhash_distance = 0
                    duplicate_count += 1
                else:
                    similar_page = _find_similar_hash(
                        page.content_dhash,
                        dhash_index,
                        settings.perceptual_hash_distance_threshold,
                    )
                    if similar_page:
                        page.page_type = "similar"
                        page.hidden = False
                        page.duplicate_of_archive_id = similar_page[1]
                        page.duplicate_of_page_index = similar_page[2]
                        page.dhash_distance = similar_page[3]
                        similar_count += 1
                    else:
                        page.page_type = "normal"
                        page.hidden = False
                        page.duplicate_of_archive_id = None
                        page.duplicate_of_page_index = None
                        page.dhash_distance = None
                    seen[page.content_md5] = (archive.id, page.page_index)

                _add_hash_to_index(dhash_index, page.content_dhash, archive.id, page.page_index)
                job.completed_items += 1
            except Exception as exc:  # noqa: BLE001 - keep processing remaining pages
                job.failed_items += 1
                job.error = str(exc)
                append_job_log(job, f"Failed {archive.filename} page {page.page_index}: {exc}")
            finally:
                db.commit()

    append_job_log(job, f"Marked {duplicate_count} duplicate page(s) and {similar_count} similar page(s).")
    finish_job(job, "failed" if job.failed_items else "completed")
    db.commit()
    return {**_job_result(job), "duplicates": duplicate_count, "similar": similar_count}


def _archive_paths(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file() and is_supported_archive(path))


def _find_similar_hash(
    content_hash: str | None,
    hash_index: dict[str, list[tuple[str, str, int]]],
    threshold: int,
) -> tuple[str, str, int, int] | None:
    if not content_hash:
        return None

    candidates = {}
    for band in hash_bands(content_hash):
        for candidate_hash, archive_id, page_index in hash_index.get(band, []):
            candidates[(archive_id, page_index)] = candidate_hash

    best: tuple[str, str, int, int] | None = None
    for (archive_id, page_index), candidate_hash in candidates.items():
        distance = hash_distance(content_hash, candidate_hash)
        if distance is None or distance > threshold:
            continue
        if best is None or distance < best[3]:
            best = (candidate_hash, archive_id, page_index, distance)
    return best


def _add_hash_to_index(
    hash_index: dict[str, list[tuple[str, str, int]]],
    content_hash: str | None,
    archive_id: str,
    page_index: int,
) -> None:
    if not content_hash:
        return
    for band in hash_bands(content_hash):
        hash_index[band].append((content_hash, archive_id, page_index))


def _index_archive_pages(db: Session, archive: Archive) -> None:
    reader = get_reader(archive.file_path)
    image_paths = reader.list_images()
    archive.pages.clear()

    for index, inner_path in enumerate(image_paths, start=1):
        content = reader.read_file(inner_path)
        width, height = get_image_size(content)
        byte_size = len(content)
        if index == 1:
            _generate_archive_cover(get_settings(), archive, content)

        archive.pages.append(
            ArchivePage(
                page_index=index,
                inner_path=inner_path,
                width=width,
                height=height,
                byte_size=byte_size,
                content_md5=md5_bytes(content),
                content_sha256=sha256_bytes(content),
                content_dhash=compute_dhash(content),
            )
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
