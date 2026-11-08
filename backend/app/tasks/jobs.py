import json

from app.db import SessionLocal, utcnow
from app.models import Alert, Device, Job, JobStatus, JobType
from app.services import discovery, provisioning
from app.tasks.celery_app import celery_app


def _load_payload(job: Job) -> dict:
    if not job.payload:
        return {}
    try:
        return json.loads(job.payload)
    except json.JSONDecodeError:
        return {}


def _execute(db, job: Job) -> dict:
    device = db.get(Device, job.device_id) if job.device_id else None
    payload = _load_payload(job)

    if job.job_type == JobType.poll:
        from app.tasks.polling import poll_device

        return poll_device(job.device_id)

    if job.job_type == JobType.discover:
        subnet = payload.get("subnet", "")
        live = discovery.scan_subnet(subnet)
        found = []
        for ip in live:
            info = discovery.probe(ip)
            existing = db.query(Device).filter(Device.ip_address == ip).first()
            if existing:
                found.append({"ip": ip, "existing": True})
                continue
            device_obj = Device(
                hostname=info.get("hostname") or ip,
                ip_address=ip,
                device_type=info.get("guessed_type") or "other",
                vendor=info.get("vendor"),
                model=info.get("model"),
                serial=info.get("serial"),
                status="up" if info.get("reachable") else "unknown",
            )
            db.add(device_obj)
            db.commit()
            found.append({"ip": ip, "existing": False, "type": device_obj.device_type.value})
        return {"subnet": subnet, "live_hosts": live, "devices": found}

    if not device:
        raise RuntimeError("Job has no device")

    from app.models import AccessMethod

    method = None
    if payload.get("access_method"):
        method = AccessMethod(payload["access_method"])

    if job.job_type == JobType.config_push:
        cred = provisioning.pick_credential(device, method, db)
        return provisioning.apply_config(device, cred, payload)

    if job.job_type == JobType.reboot:
        cred = provisioning.pick_credential(device, method, db)
        return provisioning.reboot_device(device, cred)

    if job.job_type == JobType.firmware:
        firmware_url = payload.get("firmware_url")
        if not firmware_url:
            raise RuntimeError("firmware_url required in payload")
        cred = provisioning.pick_credential(device, method, db)
        return provisioning.push_firmware(device, cred, firmware_url)

    raise RuntimeError(f"Unsupported job type: {job.job_type}")


@celery_app.task(bind=True, name="app.tasks.jobs.run_job", max_retries=0)
def run_job(self, job_id: int) -> dict:
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if not job:
            return {"error": "job not found"}
        job.status = JobStatus.running
        db.commit()
        try:
            result = _execute(db, job)
            job.status = JobStatus.succeeded
            job.result = json.dumps(result, default=str)[:8000]
        except Exception as exc:
            job.status = JobStatus.failed
            job.error = str(exc)[:2000]
            if job.device_id:
                db.add(
                    Alert(
                        device_id=job.device_id,
                        severity="error",
                        message=f"Job #{job.id} ({job.job_type.value}) failed: {exc}",
                    )
                )
        finally:
            job.finished_at = utcnow()
            db.commit()
            return {"job_id": job.id, "status": job.status.value, "error": job.error}
