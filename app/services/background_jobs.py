from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import BackgroundJob

MAX_LOG_LINES = 300
JOB_TYPES = {"scan_library", "generate_thumbnails", "check_duplicates"}


def create_background_job(db: Session, job_type: str) -> BackgroundJob:
    if job_type not in JOB_TYPES:
        raise ValueError(f"Unsupported job type: {job_type}")
    job = BackgroundJob(job_type=job_type, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def list_background_jobs(db: Session, limit: int = 50) -> list[BackgroundJob]:
    return list(
        db.scalars(select(BackgroundJob).order_by(desc(BackgroundJob.created_at), desc(BackgroundJob.id)).limit(limit))
    )


def job_to_dict(job: BackgroundJob) -> dict:
    return {
        "id": job.id,
        "job_type": job.job_type,
        "status": job.status,
        "stop_requested": job.stop_requested,
        "total_items": job.total_items,
        "completed_items": job.completed_items,
        "skipped_items": job.skipped_items,
        "failed_items": job.failed_items,
        "current_item": job.current_item,
        "error": job.error,
        "log": job.log,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "updated_at": job.updated_at,
    }


def request_job_stop(db: Session, job_id: int) -> BackgroundJob | None:
    job = db.get(BackgroundJob, job_id)
    if not job:
        return None
    if job.status in {"queued", "running"}:
        job.stop_requested = True
        append_job_log(job, "Stop requested.")
        db.commit()
        db.refresh(job)
    return job


def start_job(job: BackgroundJob, total_items: int = 0) -> None:
    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    job.finished_at = None
    job.total_items = total_items
    job.completed_items = 0
    job.skipped_items = 0
    job.failed_items = 0
    job.current_item = None
    job.error = ""


def finish_job(job: BackgroundJob, status: str = "completed") -> None:
    job.status = status
    job.current_item = None
    job.finished_at = datetime.now(timezone.utc)


def append_job_log(job: BackgroundJob, message: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    lines = [line for line in (job.log or "").splitlines() if line]
    lines.append(f"{timestamp} {message}")
    job.log = "\n".join(lines[-MAX_LOG_LINES:])


def should_stop(db: Session, job: BackgroundJob) -> bool:
    db.refresh(job)
    return job.stop_requested


def run_background_job(job_id: int) -> dict:
    from app.services.library_jobs import check_file_duplicates_job, generate_thumbnails_job, scan_library_job

    with SessionLocal() as db:
        job = db.get(BackgroundJob, job_id)
        if not job:
            return {"success": False, "error": "background job not found"}

        try:
            if job.job_type == "scan_library":
                return scan_library_job(db, job)
            if job.job_type == "generate_thumbnails":
                return generate_thumbnails_job(db, job)
            if job.job_type == "check_duplicates":
                return check_file_duplicates_job(db, job)
            raise ValueError(f"Unsupported job type: {job.job_type}")
        except Exception as exc:  # noqa: BLE001 - persisted job state is surfaced to the UI
            job.error = str(exc)
            append_job_log(job, f"Job failed: {exc}")
            finish_job(job, "failed")
            db.commit()
            return {"success": False, "error": str(exc)}
