from __future__ import annotations

import shutil
import threading
import uuid
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import ConversionJob
from app.services.conversions import conversion_job_to_dict, create_conversion_job, run_conversion_job
from app.workers.tasks import convert_archives_task

router = APIRouter(prefix="/api/conversions", tags=["conversions"])
SOURCE_EXTENSIONS = {".rar", ".cbr", ".7z", ".cb7"}


class ConversionCreate(BaseModel):
    source_path: str = Field(min_length=1)
    destination_path: str = ""
    output_extension: Literal["zip", "cbz"] = "cbz"
    overwrite: bool = False
    delete_source: bool = False


@router.get("")
def list_conversion_jobs(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    total = db.query(ConversionJob).count()
    jobs = db.scalars(
        select(ConversionJob).order_by(desc(ConversionJob.created_at), desc(ConversionJob.id)).offset(offset).limit(limit)
    ).all()
    return {"total": total, "data": [conversion_job_to_dict(job) for job in jobs]}


@router.post("")
def start_conversion_job(payload: ConversionCreate, db: Session = Depends(get_db)) -> dict:
    job = create_conversion_job(
        db,
        payload.source_path,
        payload.destination_path or None,
        payload.output_extension,
        payload.overwrite,
        payload.delete_source,
    )
    dispatch_conversion_job(job.id)
    return conversion_job_to_dict(job)


@router.post("/upload")
def upload_conversion_source(
    file: UploadFile = File(...),
    destination_path: str = Form(default=""),
    output_extension: Literal["zip", "cbz"] = Form(default="cbz"),
    overwrite: bool = Form(default=False),
    db: Session = Depends(get_db),
) -> dict:
    original_name = Path(file.filename or "").name
    suffix = Path(original_name).suffix.lower()
    if suffix not in SOURCE_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Only .rar, .cbr, .7z, and .cb7 sources can be converted.")

    settings = get_settings()
    upload_dir = settings.cache_dir / "conversion_uploads" / uuid.uuid4().hex
    upload_dir.mkdir(parents=True, exist_ok=True)
    source_path = upload_dir / original_name
    with source_path.open("wb") as handle:
        shutil.copyfileobj(file.file, handle)

    job = create_conversion_job(
        db,
        str(source_path),
        destination_path or str(settings.archive_dir),
        output_extension,
        overwrite,
        True,
    )
    dispatch_conversion_job(job.id)
    return conversion_job_to_dict(job)


@router.get("/tools")
def conversion_tools() -> dict:
    return {
        "zip": bool(shutil.which("zip")),
        "unrar": bool(shutil.which("unrar")),
        "seven_zip": bool(shutil.which("7zz") or shutil.which("7z")),
        "unar": bool(shutil.which("unar")),
    }


@router.get("/{job_id}")
def get_conversion_job(job_id: int, db: Session = Depends(get_db)) -> dict:
    job = db.get(ConversionJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Conversion job not found")
    return conversion_job_to_dict(job)


def dispatch_conversion_job(job_id: int) -> None:
    if get_settings().celery_task_always_eager:
        threading.Thread(target=run_conversion_job, args=(job_id,), daemon=True).start()
    else:
        convert_archives_task.delay(job_id)
