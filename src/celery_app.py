import os

from celery import Celery
from celery.signals import worker_ready

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "documents",
    broker=REDIS_URL,
    backend=REDIS_URL,
)
celery_app.conf.task_track_started = True


@worker_ready.connect
def on_worker_ready(**kwargs):
    """Load models when worker is ready to accept tasks"""
    import src.embedding
    from langchain_experimental.text_splitter import SemanticChunker

    src.embedding.chunker = SemanticChunker(embeddings=src.embedding.embedder)
