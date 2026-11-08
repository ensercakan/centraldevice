from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db, log_action, require_roles
from app.models import Job, JobStatus, JobType, Role, User
from app.schemas import JobOut

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("", response_model=list[JobOut])
def list_jobs(
    job_type: JobType | None = Query(default=None),
    job_status: JobStatus | None = Query(default=None, alias="status"),
    device_id: int | None = Query(default=None),
    limit: int = Query(default=200, le=1000),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    query = db.query(Job)
    if job_type is not None:
        query = query.filter(Job.job_type == job_type)
    if job_status is not None:
        query = query.filter(Job.status == job_status)
    if device_id is not None:
        query = query.filter(Job.device_id == device_id)
    return query.order_by(Job.id.desc()).limit(limit).all()


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.post("/{job_id}/retry", response_model=JobOut)
def retry_job(job_id: int, db: Session = Depends(get_db), current: User = Depends(require_roles(Role.admin, Role.operator))):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status == JobStatus.running:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job is already running")
    job.status = JobStatus.queued
    job.error = None
    db.commit()
    db.refresh(job)
    from app.tasks.jobs import run_job

    try:
        run_job.delay(job.id)
    except Exception:
        run_job(job.id)
    db.refresh(job)
    log_action(db, current, "job.retry", target=str(job.id))
    return job
