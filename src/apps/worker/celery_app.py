from celery import Celery

from src.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)
celery_app.conf.task_track_started = True

# Note: autodiscover_tasks is NOT called here to prevent ModelManager loading
# in non-worker processes (e.g., public API). Tasks are registered explicitly
# in src/services/ingestion/tasks.py using @celery_app.task decorator.
