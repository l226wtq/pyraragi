from __future__ import annotations

import threading
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.db.session import get_db
from app.models import BackgroundJob, FileDuplicateGroup
from app.services.background_jobs import create_background_job, job_to_dict, list_background_jobs, request_job_stop
from app.services.background_jobs import run_background_job
from app.workers.tasks import background_job_task

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("")
def list_jobs(limit: int = Query(default=50, ge=1, le=100), db: Session = Depends(get_db)) -> dict:
    jobs = list_background_jobs(db, limit)
    return {"data": [job_to_dict(job) for job in jobs]}


@router.post("/{job_type}")
def start_job(
    job_type: Literal["scan_library", "generate_thumbnails", "check_duplicates"],
    db: Session = Depends(get_db),
) -> dict:
    job = create_background_job(db, job_type)
    dispatch_job(job.id)
    return job_to_dict(job)


@router.get("/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)) -> dict:
    job = db.get(BackgroundJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_to_dict(job)


@router.post("/{job_id}/stop")
def stop_job(job_id: int, db: Session = Depends(get_db)) -> dict:
    job = request_job_stop(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_to_dict(job)


@router.get("/duplicates/groups")
def list_duplicate_groups(db: Session = Depends(get_db)) -> dict:
    groups = db.scalars(
        select(FileDuplicateGroup)
        .options(selectinload(FileDuplicateGroup.members))
        .order_by(desc(FileDuplicateGroup.member_count), desc(FileDuplicateGroup.created_at))
    ).all()
    return {
        "data": [
            {
                "id": group.id,
                "file_size": group.file_size,
                "partial_hash": group.partial_hash,
                "full_sha256": group.full_sha256,
                "member_count": group.member_count,
                "created_at": group.created_at,
                "members": [
                    {
                        "archive_id": member.archive_id,
                        "file_path": member.file_path,
                        "filename": member.filename,
                        "file_size": member.file_size,
                    }
                    for member in group.members
                ],
            }
            for group in groups
        ]
    }


def dispatch_job(job_id: int) -> None:
    if get_settings().celery_task_always_eager:
        threading.Thread(target=run_background_job, args=(job_id,), daemon=True).start()
    else:
        background_job_task.delay(job_id)
