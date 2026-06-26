from celery import Celery
import config

celery_app = Celery(
    "pulseiq", broker=config.REDIS_URL, backend=config.REDIS_URL, include=["tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "pipeline-every-5-minutes": {
            "task": "tasks.run_pipeline",
            "schedule": 300.0,
        }
    },
)
