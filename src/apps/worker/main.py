"""Celery worker entry point."""
import logging
import sys

import src.services.ingestion.tasks  # noqa: F401
from src.apps.worker.celery_app import celery_app
from src.core.models import get_model_manager

logger = logging.getLogger(__name__)


def init_worker():
    """Initialize worker: load models once at startup."""
    logger.info("🚀 Celery Worker starting...")

    try:
        model_manager = get_model_manager()
        model_manager.initialize_for_worker()
        logger.info("✓ Worker models initialized (embedder + chunker)")
    except Exception as e:
        logger.error(f"✗ Failed to initialize worker models: {e}")
        sys.exit(1)

    logger.info("✓ Worker ready")


if __name__ == "__main__":
    # Pre-load models BEFORE starting worker
    init_worker()

    # Now start Celery worker
    celery_app.worker_main([
        "worker",
        "--loglevel=info",
    ])
