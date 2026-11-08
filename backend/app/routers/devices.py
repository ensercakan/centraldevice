import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db, log_action, require_roles
from app.models import AccessMethod, Credential, Device, DeviceType, Job, JobType, Role, User
from app.schemas import (
    ConfigPushRequest,
    CredentialCreate,
    CredentialOut,
    DeviceCreate,
    DeviceOut,
    DeviceUpdate,
    DeviceWithRelations,
    DiscoverRequest,
)
from app.security import encrypt_secret

router = APIRouter(prefix="/api/devices", tags=["devices"])


def enqueue_job(db: Session, user: User, device_id: int | None, job_type: JobType, payload: dict | None) -> Job:
    job = Job(
        device_id=device_id,
        job_type=job_type,
        payload=json.dumps(payload) if payload else None,
        created_by=user.id if user else None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    from app.tasks.jobs import run_job

    try:
        run_job.delay(job.id)
    except Exception:
        run_job(job.id)
    return job


def get_device_or_404(db: Session, device_id: int) -> Device:
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return device


@router.get("", response_model=list[DeviceOut])
def list_devices(
    device_type: DeviceType | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    query = db.query(Device)
    if device_type is not None:
        query = query.filter(Device.device_type == device_type)
    if status_filter:
        query = query.filter(Device.status == status_filter)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Device.hostname.ilike(like)) | (Device.ip_address.ilike(like)) | (Device.site.ilike(like))
        )
    return query.order_by(Device.id).all()


@router.post("", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
def create_device(
    payload: DeviceCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(Role.admin, Role.operator)),
):
    if db.query(Device).filter(Device.ip_address == payload.ip_address).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="IP address already registered")
    device = Device(**payload.model_dump())
    db.add(device)
    db.commit()
    db.refresh(device)
    log_action(db, current, "device.create", target=device.ip_address, detail=device.hostname)
    return device


@router.post("/discover")
def discover(payload: DiscoverRequest, db: Session = Depends(get_db), current: User = Depends(require_roles(Role.admin, Role.operator))):
    job = enqueue_job(db, current, None, JobType.discover, {"subnet": payload.subnet})
    return {"job_id": job.id, "status": job.status.value}


@router.get("/{device_id}", response_model=DeviceWithRelations)
def get_device(device_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return get_device_or_404(db, device_id)


@router.patch("/{device_id}", response_model=DeviceOut)
def update_device(
    device_id: int,
    payload: DeviceUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(Role.admin, Role.operator)),
):
    device = get_device_or_404(db, device_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(device, key, value)
    db.commit()
    db.refresh(device)
    log_action(db, current, "device.update", target=device.ip_address)
    return device


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(Role.admin)),
):
    device = get_device_or_404(db, device_id)
    log_action(db, current, "device.delete", target=device.ip_address, detail=device.hostname)
    db.delete(device)
    db.commit()
    return None


@router.post("/{device_id}/credentials", response_model=CredentialOut, status_code=status.HTTP_201_CREATED)
def add_credential(
    device_id: int,
    payload: CredentialCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(Role.admin, Role.operator)),
):
    device = get_device_or_404(db, device_id)
    cred = Credential(
        name=payload.name,
        device_id=device.id,
        access_method=payload.access_method,
        encrypted_secret=encrypt_secret(payload.secret),
    )
    db.add(cred)
    db.commit()
    db.refresh(cred)
    log_action(db, current, "credential.create", target=f"device:{device.ip_address}", detail=payload.access_method.value)
    return cred


@router.get("/{device_id}/credentials", response_model=list[CredentialOut])
def list_credentials(device_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    device = get_device_or_404(db, device_id)
    return device.credentials


@router.delete("/{device_id}/credentials/{cred_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_credential(
    device_id: int,
    cred_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(Role.admin, Role.operator)),
):
    cred = db.query(Credential).filter(Credential.id == cred_id, Credential.device_id == device_id).first()
    if not cred:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")
    log_action(db, current, "credential.delete", target=f"device:{device_id}", detail=str(cred_id))
    db.delete(cred)
    db.commit()
    return None


@router.post("/{device_id}/poll")
def poll_device(device_id: int, db: Session = Depends(get_db), current: User = Depends(require_roles(Role.admin, Role.operator))):
    device = get_device_or_404(db, device_id)
    job = enqueue_job(db, current, device.id, JobType.poll, None)
    log_action(db, current, "device.poll", target=device.ip_address)
    return {"job_id": job.id, "status": job.status.value}


@router.post("/{device_id}/config")
def push_config(
    device_id: int,
    payload: ConfigPushRequest,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(Role.admin, Role.operator)),
):
    device = get_device_or_404(db, device_id)
    method = payload.access_method
    if method is None:
        cred = db.query(Credential).filter(Credential.device_id == device.id).first()
        method = cred.access_method if cred else AccessMethod.ssh
    job = enqueue_job(
        db,
        current,
        device.id,
        JobType.config_push,
        {"template": payload.template, "variables": payload.variables, "access_method": method.value},
    )
    log_action(db, current, "device.config_push", target=device.ip_address)
    return {"job_id": job.id, "status": job.status.value}


@router.post("/{device_id}/reboot")
def reboot_device(device_id: int, db: Session = Depends(get_db), current: User = Depends(require_roles(Role.admin, Role.operator))):
    device = get_device_or_404(db, device_id)
    job = enqueue_job(db, current, device.id, JobType.reboot, None)
    log_action(db, current, "device.reboot", target=device.ip_address)
    return {"job_id": job.id, "status": job.status.value}


@router.get("/{device_id}/metrics")
def get_metrics(
    device_id: int,
    metric_key: str | None = Query(default=None),
    limit: int = Query(default=100, le=1000),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    get_device_or_404(db, device_id)
    from app.models import DeviceMetric

    query = db.query(DeviceMetric).filter(DeviceMetric.device_id == device_id)
    if metric_key:
        query = query.filter(DeviceMetric.metric_key == metric_key)
    rows = query.order_by(DeviceMetric.ts.desc()).limit(limit).all()
    return [
        {"ts": row.ts, "metric_key": row.metric_key, "value": row.value}
        for row in reversed(rows)
    ]
