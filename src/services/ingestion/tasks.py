"""Document ingestion tasks."""
import logging

from src.apps.worker.celery_app import celery_app
from src.core.config import settings
from src.core.db import SessionLocal
from src.db.models import Chunk, Document
from src.services.ingestion.chunking import ChunkingService
from src.services.ingestion.embedding import EmbeddingService

logger = logging.getLogger(__name__)


@celery_app.task(name="src.services.ingestion.tasks.process_document_task")
def process_document_task(doc_id: str):
    """
    Async task: read document, chunk text, embed chunks, store in database.

    Models are pre-loaded when worker starts via initialize_for_worker().
    """
    try:
        logger.info(f"Processing document {doc_id}...")
        dest_path = f"{settings.DOCUMENT_STORAGE_PATH}/{doc_id}"

        # Read document
        try:
            with open(dest_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            logger.error(f"Document {doc_id} is not valid UTF-8 text; not retrying")
            raise
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
        chunk_embeds = embedder.embed(chunks)
        logger.debug(f"Embedded {len(chunk_embeds)} chunks")

        # Store chunks in database
        db = SessionLocal()

        doc_record = db.query(Document).filter(Document.id == doc_id).first()
        if not doc_record:
            raise ValueError(f"Document {doc_id} not found")

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
            db.delete(doc_record)
            db.commit()
            logger.error(f"Failed to store chunks: {e}")
            raise
        finally:
            db.close()

        logger.info(f"✓ Document {doc_id} processed successfully")

    except Exception as e:
        logger.error(f"Error processing document {doc_id}: {e}")
        raise
