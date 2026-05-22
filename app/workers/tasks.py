from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

from app.archive.identity import compute_archive_id, md5_bytes, sha256_bytes
from app.archive.reader import get_reader
from app.archive.types import is_supported_archive
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.image.fingerprints import compute_dhash, compute_phash
from app.image.thumbnails import generate_thumbnail, get_image_size
from app.models import Archive, ArchivePage, ArchiveTag, Tag
from app.services.background_jobs import run_background_job
from app.services.conversions import run_conversion_job
from app.workers.celery_app import celery_app


@celery_app.task(name="index_archive")
def index_archive_task(archive_id: str, tags: str = "") -> dict:
    settings = get_settings()
    with SessionLocal() as db:
        archive = db.get(Archive, archive_id)
        if not archive:
            return {"success": False, "error": "archive not found"}

        reader = get_reader(archive.file_path)
        image_paths = reader.list_images()

        archive.pages.clear()
        for index, inner_path in enumerate(image_paths, start=1):
            page_content = reader.read_file(inner_path)
            width, height = get_image_size(page_content)
            byte_size = len(page_content)
            if index == 1:
                thumbnail_format = normalize_thumbnail_format(settings.thumbnail_format)
                thumb_path = settings.thumb_dir / archive.id[:2] / f"{archive.id}.{thumbnail_format}"
                archive.cover_hash = generate_thumbnail(page_content, thumb_path, output_format=thumbnail_format)
                archive.cover_path = str(thumb_path)

            archive.pages.append(
                ArchivePage(
                    page_index=index,
                    inner_path=inner_path,
                    width=width,
                    height=height,
                    byte_size=byte_size,
                    content_md5=md5_bytes(page_content),
                    content_sha256=sha256_bytes(page_content),
                    content_dhash=compute_dhash(page_content),
                    content_phash=compute_phash(page_content),
                )
            )

        archive.page_count = len(image_paths)
        _replace_tags(db, archive, tags)
        db.commit()
        return {"success": True, "pages": len(image_paths)}


@celery_app.task(name="scan_library")
def scan_library_task() -> dict:
    settings = get_settings()
    imported = 0
    skipped = 0
    with SessionLocal() as db:
        for path in settings.archive_dir.iterdir():
            if not path.is_file() or not is_supported_archive(path):
                continue

            archive_id = compute_archive_id(path)
            archive = db.get(Archive, archive_id)
            if archive:
                skipped += 1
                continue

            stat = path.stat()
            archive = Archive(
                id=archive_id,
                title=path.stem,
                filename=path.name,
                file_path=str(path),
                extension=path.suffix.lower().lstrip("."),
                file_size=stat.st_size,
                partial_hash=archive_id,
            )
            db.add(archive)
            db.commit()
            index_archive_task.run(archive.id, "")
            imported += 1

    return {"success": True, "imported": imported, "skipped": skipped}


@celery_app.task(name="convert_archives")
def convert_archives_task(job_id: int) -> dict:
    return run_conversion_job(job_id)


@celery_app.task(name="background_job")
def background_job_task(job_id: int) -> dict:
    return run_background_job(job_id)


def _replace_tags(db, archive: Archive, tags: str) -> None:
    archive.tag_links.clear()
    parsed = [_parse_tag(item) for item in tags.split(",") if item.strip()]
    for namespace, name in parsed:
        normalized_name = name.lower()
        tag = db.scalar(select(Tag).where(Tag.namespace == namespace, Tag.normalized_name == normalized_name))
        if not tag:
            tag = Tag(namespace=namespace, name=name, normalized_name=normalized_name)
            db.add(tag)
            db.flush()
        archive.tag_links.append(ArchiveTag(tag=tag))


def _parse_tag(raw: str) -> tuple[str, str]:
    value = raw.strip()
    if ":" in value:
        namespace, name = value.split(":", 1)
        return namespace.strip().lower(), name.strip()
    return "", value


def normalize_thumbnail_format(value: str) -> str:
    value = (value or "webp").lower().lstrip(".")
    if value == "jpeg":
        return "jpg"
    if value in {"webp", "jxl", "jpg"}:
        return value
    return "webp"
