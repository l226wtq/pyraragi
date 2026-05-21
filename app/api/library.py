from fastapi import APIRouter

from app.workers.tasks import scan_library_task

router = APIRouter(prefix="/api/library", tags=["library"])


@router.post("/scan")
def scan_library() -> dict:
    job = scan_library_task.delay()
    return {"queued": True, "job_id": job.id}
