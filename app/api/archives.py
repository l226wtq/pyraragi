from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.archives import archive_to_dict, get_archive, list_archives
from app.schemas.archive import ArchiveOut, SearchResult, UploadResult
from app.services.importer import import_uploaded_archive
from app.services.pages import read_page_bytes

router = APIRouter(prefix="/api/archives", tags=["archives"])


@router.get("", response_model=SearchResult)
def search_archives(
    q: str = "",
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=60, ge=1, le=200),
    sort: str = "title",
    desc: bool = False,
    db: Session = Depends(get_db),
) -> dict:
    total, archives = list_archives(db, q, offset, limit, sort, desc)
    return {"total": total, "data": [archive_to_dict(archive) for archive in archives]}


@router.post("", response_model=UploadResult)
def upload_archive(
    file: UploadFile = File(...),
    tags: str = Form(default=""),
    db: Session = Depends(get_db),
) -> dict:
    suffix = Path(file.filename or "").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
        shutil.copyfileobj(file.file, handle)
        temp_path = Path(handle.name)

    try:
        archive = import_uploaded_archive(db, temp_path, file.filename or temp_path.name, tags)
    except ValueError as exc:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=415, detail=str(exc)) from exc

    return {"id": archive.id, "title": archive.title, "queued": True}


@router.get("/{archive_id}", response_model=ArchiveOut)
def get_archive_detail(archive_id: str, db: Session = Depends(get_db)) -> dict:
    archive = get_archive(db, archive_id)
    if not archive:
        raise HTTPException(status_code=404, detail="Archive not found")
    return archive_to_dict(archive)


@router.get("/{archive_id}/cover")
def get_cover(archive_id: str, db: Session = Depends(get_db)) -> FileResponse:
    archive = get_archive(db, archive_id)
    if not archive or not archive.cover_path:
        raise HTTPException(status_code=404, detail="Cover not ready")
    cover_path = Path(archive.cover_path)
    if not cover_path.exists():
        raise HTTPException(status_code=404, detail="Cover not found")
    return FileResponse(cover_path, media_type=_media_type(cover_path.name))


@router.get("/{archive_id}/pages")
def list_pages(archive_id: str, db: Session = Depends(get_db)) -> dict:
    archive = get_archive(db, archive_id)
    if not archive:
        raise HTTPException(status_code=404, detail="Archive not found")
    return {
        "id": archive.id,
        "page_count": archive.page_count,
        "pages": [
            {
                "page_index": page.page_index,
                "inner_path": page.inner_path,
                "width": page.width,
                "height": page.height,
                "byte_size": page.byte_size,
                "content_md5": page.content_md5,
                "content_sha256": page.content_sha256,
                "content_dhash": page.content_dhash,
                "content_phash": page.content_phash,
                "dhash_distance": page.dhash_distance,
                "phash_distance": page.phash_distance,
                "page_type": page.page_type,
                "hidden": page.hidden,
                "duplicate_of_archive_id": page.duplicate_of_archive_id,
                "duplicate_of_page_index": page.duplicate_of_page_index,
            }
            for page in archive.pages
        ],
    }


@router.get("/{archive_id}/page/{page_index}")
def get_page(archive_id: str, page_index: int, db: Session = Depends(get_db)) -> Response:
    _, page, content = read_page_bytes(db, archive_id, page_index)
    media_type = _media_type(page.inner_path)
    return Response(content=content, media_type=media_type, headers={"Cache-Control": "private, max-age=3600"})


def _media_type(path: str) -> str:
    suffix = Path(path).suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".avif": "image/avif",
        ".jxl": "image/jxl",
        ".jpegxl": "image/jxl",
    }.get(suffix, "application/octet-stream")
