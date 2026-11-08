from celery import Celery

from app.config import settings

celery_app = Celery(
    "centraldevice",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.polling", "app.tasks.jobs"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "poll-all-devices": {
            "task": "app.tasks.polling.poll_all_devices",
            "schedule": float(settings.poll_interval_seconds),
        }
    },
)
