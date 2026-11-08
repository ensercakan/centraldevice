import json

from sqlalchemy.orm import Session

from app.db import SessionLocal, utcnow
from app.models import AccessMethod, Alert, Credential, Device, DeviceMetric
from app.services import snmp_service
from app.tasks.celery_app import celery_app


def store_metrics(db: Session, device_id: int, data: dict) -> None:
    ts = utcnow()
    for key, value in data.items():
        if key in ("interfaces",) or value is None:
            continue
        db.add(DeviceMetric(device_id=device_id, ts=ts, metric_key=key, value=str(value)))
    if "interfaces" in data:
        db.add(DeviceMetric(device_id=device_id, ts=ts, metric_key="interfaces_total", value=str(len(data["interfaces"]))))
        db.add(DeviceMetric(device_id=device_id, ts=ts, metric_key="interfaces_up", value=str(data.get("interfaces_up", 0))))


def mark_down(db: Session, device: Device, reason: str) -> None:
    device.status = "down"
    existing = (
        db.query(Alert)
        .filter(Alert.device_id == device.id, Alert.acknowledged.is_(False), Alert.message == reason)
        .first()
    )
    if not existing:
        db.add(Alert(device_id=device.id, severity="critical", message=reason))


@celery_app.task(name="app.tasks.polling.poll_device")
def poll_device(device_id: int) -> dict:
    with SessionLocal() as db:
        device = db.get(Device, device_id)
        if not device:
            return {"error": "device not found"}
        cred = (
            db.query(Credential)
            .filter(Credential.device_id == device.id, Credential.access_method == AccessMethod.snmp)
            .first()
        )
        community = "public"
        port = None
        if cred:
            from app.security import decrypt_secret

            secret = decrypt_secret(cred.encrypted_secret)
            community = secret.get("community", "public")
            port = int(secret.get("port", 0)) or None
        data = snmp_service.poll(device.ip_address, community, port=port)
        if data.get("reachable") == "yes":
            device.status = "up"
            device.last_seen = utcnow()
            if data.get("vendor") and not device.vendor:
                device.vendor = data["vendor"]
            if data.get("model") and not device.model:
                device.model = data["model"]
            if data.get("serial") and not device.serial:
                device.serial = data["serial"]
            store_metrics(db, device.id, data)
            db.commit()
            return {"status": "up", "metrics": {k: v for k, v in data.items() if k != "interfaces"}}
        device.status = "down"
        mark_down(db, device, f"SNMP unreachable: {device.ip_address} ({device.hostname})")
        db.commit()
        return {"status": "down"}


@celery_app.task(name="app.tasks.polling.poll_all_devices")
def poll_all_devices() -> dict:
    with SessionLocal() as db:
        device_ids = [row[0] for row in db.query(Device.id).all()]
    for device_id in device_ids:
        poll_device.delay(device_id)
    return {"queued": len(device_ids)}
