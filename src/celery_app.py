import os

from celery import Celery
from celery.signals import worker_process_init

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "documents",
    broker=REDIS_URL,
    backend=REDIS_URL,
)
celery_app.conf.task_track_started = True


@worker_process_init.connect
def on_worker_process_init(**kwargs):
    """Load embedder + chunker once, at worker cold start, not on first task."""
    import src.embedding
    src.embedding.load_embedder()
    src.embedding.load_chunker()
