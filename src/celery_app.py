import os

from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "documents",
    broker=REDIS_URL,
    backend=REDIS_URL,
)
celery_app.conf.task_track_started = True
