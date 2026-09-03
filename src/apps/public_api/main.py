import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.apps.public_api.routes import documents, query
from src.apps.worker.queue import CeleryQueue
from src.core.config import settings
from src.core.errors import DomainException, domain_exception_handler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: initialize queue on startup, cleanup on shutdown."""
    # Startup
    logger.info("Starting up public_api...")
    try:
        from src.apps.worker.celery_app import celery_app
        CeleryQueue.init(celery_app)
        logger.info("✓ CeleryQueue initialized")
    except Exception as e:
        logger.error(f"✗ Failed to initialize CeleryQueue: {e}")
        raise

    client = None
    try:
        from src.apps.public_api.grpc_client import get_retrieval_client
        client = get_retrieval_client()
        client.init()
        logger.info("✓ gRPC retrieval client initialized")
    except Exception as e:
        logger.error(f"✗ Failed to initialize gRPC retrieval client: {e}")
        raise

    yield

    # Shutdown
    if client:
        client.close()
    logger.info("Shutting down public_api...")
    logger.info("✓ Cleanup complete")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="RAG-based document intelligence platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Exception handlers
app.add_exception_handler(DomainException, domain_exception_handler)

# Routes
app.include_router(documents.router, prefix="/v1")
app.include_router(query.router, prefix="/v1")


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok", "service": "public_api"}
