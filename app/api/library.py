import threading

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.services.background_jobs import create_background_job, job_to_dict, run_background_job
from app.workers.tasks import background_job_task

router = APIRouter(prefix="/api/library", tags=["library"])


@router.post("/scan")
def scan_library(db: Session = Depends(get_db)) -> dict:
    job = create_background_job(db, "scan_library")
    if get_settings().celery_task_always_eager:
        threading.Thread(target=run_background_job, args=(job.id,), daemon=True).start()
    else:
        background_job_task.delay(job.id)
    return {"queued": True, "job_id": job.id, "job": job_to_dict(job)}
