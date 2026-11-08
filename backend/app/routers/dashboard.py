from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import utcnow
from app.deps import get_current_user, get_db
from app.models import Alert, Device, Job, User
from app.schemas import DashboardSummary

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def summary(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    devices = db.query(Device).all()
    by_type: dict[str, int] = {}
    for device in devices:
        key = device.device_type.value if device.device_type else "other"
        by_type[key] = by_type.get(key, 0) + 1
    up = sum(1 for d in devices if d.status == "up")
    down = sum(1 for d in devices if d.status == "down")
    unknown = sum(1 for d in devices if d.status not in ("up", "down"))
    open_alerts = db.query(func.count(Alert.id)).filter(Alert.acknowledged.is_(False)).scalar() or 0
    since = utcnow() - timedelta(hours=24)
    jobs_24h = db.query(func.count(Job.id)).filter(Job.created_at >= since).scalar() or 0
    recent_alerts = db.query(Alert).order_by(Alert.id.desc()).limit(10).all()
    recent_jobs = db.query(Job).order_by(Job.id.desc()).limit(10).all()
    return DashboardSummary(
        devices_total=len(devices),
        devices_up=up,
        devices_down=down,
        devices_unknown=unknown,
        by_type=by_type,
        open_alerts=open_alerts,
        jobs_last_24h=jobs_24h,
        recent_alerts=recent_alerts,
        recent_jobs=recent_jobs,
    )
