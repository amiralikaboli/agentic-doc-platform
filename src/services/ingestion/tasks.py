"""Document ingestion tasks."""
import logging

from src.services.ingestion.embedding import EmbeddingService
from src.services.ingestion.chunking import ChunkingService
from src.apps.worker.celery_app import celery_app
from src.core.db import SessionLocal
from src.db.models import Chunk
from src.core.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, name="src.services.ingestion.tasks.process_document_task")
def process_document_task(self, doc_id: str):
    """
    Async task: read document, chunk text, embed chunks, store in database.

    Retries up to 3 times on failure.
    Models are pre-loaded when worker starts via initialize_for_worker().
    """
    try:
        logger.info(f"Processing document {doc_id}...")
        dest_path = f"{settings.DOCUMENT_STORAGE_PATH}/{doc_id}"

        # Read document
        with open(dest_path, "r", encoding="utf-8") as f:
            content = f.read()
        logger.debug(f"Read {len(content)} characters from {doc_id}")

        # Services use pre-loaded models from ModelManager (initialized in worker startup)
        embedder = EmbeddingService()
        chunker = ChunkingService()

        # Chunk text
        chunks = chunker.split_text(content)
        if not chunks:
            raise ValueError(f"No text chunks could be extracted from document {doc_id}")
        logger.info(f"Created {len(chunks)} chunks for {doc_id}")

        # Embed chunks
        chunk_embeds = embedder.embed_batch(chunks)
        logger.debug(f"Embedded {len(chunk_embeds)} chunks")

        # Store chunks in database
        db = SessionLocal()
        try:
            for idx, (text, embed) in enumerate(zip(chunks, chunk_embeds)):
                db.add(
                    Chunk(
                        document_id=doc_id,
                        content=text,
                        chunk_index=idx,
                        embedding=embed,
                    )
                )
            db.commit()
            logger.info(f"Stored {len(chunks)} chunks for document {doc_id}")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to store chunks: {e}")
            raise
        finally:
            db.close()

        logger.info(f"✓ Document {doc_id} processed successfully")

    except Exception as e:
        logger.error(f"Error processing document {doc_id}: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries)
