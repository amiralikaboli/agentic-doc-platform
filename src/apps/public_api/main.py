"""FastAPI public API application."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.apps.public_api.routes import documents, query
from src.core.config import settings
from src.core.errors import DomainException, domain_exception_handler


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("🚀 API Server starting...")
    logger.info("✓ API Server ready (no models needed — embedder in retrieval service)")

    yield  # App runs here

    # Shutdown
    logger.info("🛑 API Server shutting down...")


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
    """Health check endpoint."""
    return {"status": "ok", "service": "public_api"}
