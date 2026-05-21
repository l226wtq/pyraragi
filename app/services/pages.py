from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.archive.reader import get_reader
from app.models import Archive, ArchivePage
from app.repositories.archives import get_archive


def read_page_bytes(db: Session, archive_id: str, page_index: int) -> tuple[Archive, ArchivePage, bytes]:
    archive = get_archive(db, archive_id)
    if not archive:
        raise HTTPException(status_code=404, detail="Archive not found")

    page = next((item for item in archive.pages if item.page_index == page_index), None)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    reader = get_reader(Path(archive.file_path))
    return archive, page, reader.read_file(page.inner_path)
