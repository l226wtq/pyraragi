from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.archive.identity import compute_archive_id
from app.archive.types import is_supported_archive
from app.core.config import get_settings
from app.models import Archive
from app.workers.tasks import index_archive_task


def import_uploaded_archive(db: Session, source_path: Path, original_filename: str, tags: str = "") -> Archive:
    if not is_supported_archive(original_filename):
        raise ValueError("Only .zip and .cbz archives are supported.")

    settings = get_settings()
    archive_id = compute_archive_id(source_path)
    extension = Path(original_filename).suffix.lower()
    safe_name = f"{archive_id}{extension}"
    target = settings.archive_dir / safe_name
    shutil.move(str(source_path), target)

    existing = db.scalar(select(Archive).where(Archive.id == archive_id))
    stat = target.stat()
    if existing:
        existing.file_path = str(target)
        existing.file_size = stat.st_size
        existing.file_mtime = datetime.fromtimestamp(stat.st_mtime, timezone.utc)
        archive = existing
    else:
        title = Path(original_filename).stem
        archive = Archive(
            id=archive_id,
            title=title,
            filename=original_filename,
            file_path=str(target),
            extension=extension.lstrip("."),
            file_size=stat.st_size,
            file_mtime=datetime.fromtimestamp(stat.st_mtime, timezone.utc),
        )
        db.add(archive)

    db.commit()
    db.refresh(archive)
    index_archive_task.delay(archive.id, tags)
    return archive
