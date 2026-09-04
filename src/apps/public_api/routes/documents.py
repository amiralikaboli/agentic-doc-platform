import logging
import os
import shutil
import uuid

from fastapi import UploadFile, Header, Response, APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.public_api.schemas.documents import (
    ErrorResponse,
    DocumentOut,
    DocumentStatusOut,
    PaginatedDocuments,
    DocumentStatus,
)
from src.apps.worker.queue import get_queue
from src.core.config import settings
from src.core.db import get_db
from src.core.errors import ResourceNotFound, ValidationError, InternalServerError
from src.db.models import Document

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Documents"])


@router.post("/documents", status_code=202, response_model=DocumentOut, responses={422: {"model": ErrorResponse}})
async def create_document(
        response: Response,
        file: UploadFile,
        idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
        db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    try:
        if file.content_type != "text/plain":
            raise ValidationError("Only text/plain files are allowed", {"content_type": file.content_type})

        # Check idempotency
        if idempotency_key:
            stmt = select(Document).where(Document.idempotency_key == idempotency_key)
            result = await db.execute(stmt)
            existing = result.scalars().first()
            if existing:
                response.headers["Location"] = f"/v1/documents/{existing.id}"
                return DocumentOut.model_validate(existing, from_attributes=True)

        # Generate document ID
        doc_id = str(uuid.uuid4())
        dest_path = os.path.join(settings.DOCUMENT_STORAGE_PATH, doc_id)

        # Ensure storage directory exists
        os.makedirs(settings.DOCUMENT_STORAGE_PATH, exist_ok=True)

        # Save file
        try:
            with open(dest_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            file_size = os.path.getsize(dest_path)
        except Exception as e:
            logger.error(f"Failed to save file: {e}")
            if os.path.exists(dest_path):
                os.remove(dest_path)
            raise InternalServerError("Failed to save uploaded file")

        # Create document record
        record = Document(
            id=doc_id,
            filename=file.filename,
            content_type=file.content_type,
            size=file_size,
            idempotency_key=idempotency_key,
        )
        db.add(record)

        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            if os.path.exists(dest_path):
                os.remove(dest_path)
            raise InternalServerError("Failed to create document record")

        # Enqueue async processing task
        try:
            queue = get_queue()
            task = queue.send_task(
                "src.services.ingestion.tasks.process_document_task",
                args=(doc_id,),
            )
            record.task_id = task.id
            await db.commit()
            logger.info(f"Document {doc_id} enqueued for processing (task_id={task.id})")
        except Exception as e:
            logger.error(f"Failed to enqueue processing task: {e}")
            raise InternalServerError("Failed to enqueue document for processing")

        response.headers["Location"] = f"/v1/documents/{doc_id}"
        return DocumentOut.model_validate(record, from_attributes=True)

    except Exception as e:
        if not isinstance(e, (ResourceNotFound, ValidationError, InternalServerError)):
            logger.error(f"Unexpected error in create_document: {e}")
        raise


@router.get("/documents/{id}", response_model=DocumentOut, responses={404: {"model": ErrorResponse}})
async def get_document(id: str, db: AsyncSession = Depends(get_db)) -> DocumentOut:
    """Retrieve document metadata."""
    stmt = select(Document).where(Document.id == id)
    result = await db.execute(stmt)
    record = result.scalars().first()

    if not record:
        raise ResourceNotFound("Document", str(id))

    return DocumentOut.model_validate(record, from_attributes=True)


@router.delete("/documents/{id}", status_code=204, responses={404: {"model": ErrorResponse}})
async def delete_document(id: str, db: AsyncSession = Depends(get_db)) -> Response:
    """Delete a document and its associated chunks."""
    stmt = select(Document).where(Document.id == id)
    result = await db.execute(stmt)
    record = result.scalars().first()

    if not record:
        raise ResourceNotFound("Document", str(id))

    try:
        # Revoke processing task if still running
        if record.task_id:
            queue = get_queue()
            queue.revoke_task(record.task_id, terminate=True)
            logger.info(f"Revoked task {record.task_id}")

        await db.delete(record)
        await db.commit()
        logger.info(f"Document {id} deleted from database")

        # Delete file
        dest_path = os.path.join(settings.DOCUMENT_STORAGE_PATH, str(id))
        if os.path.exists(dest_path):
            os.remove(dest_path)
            logger.info(f"Document file {dest_path} deleted")

    except Exception as e:
        logger.error(f"Error deleting document {id}: {e}")
        raise InternalServerError(f"Failed to delete document: {str(e)}")

    return Response(status_code=204)


@router.get("/documents/{id}/status", response_model=DocumentStatusOut, responses={404: {"model": ErrorResponse}})
async def get_document_status(id: str, db: AsyncSession = Depends(get_db)) -> DocumentStatusOut:
    """Get the processing status of a document."""
    stmt = select(Document).where(Document.id == id)
    result = await db.execute(stmt)
    record = result.scalars().first()

    if not record:
        raise ResourceNotFound("Document", str(id))

    queue = get_queue()
    task = queue.get_task_result(record.task_id)
    status, error_reason = DocumentStatus.map_task_state(task.state if task else "PENDING",
                                                         task.result if task else None)

    return DocumentStatusOut(id=record.id, status=status, error_reason=error_reason)


@router.get("/documents", response_model=PaginatedDocuments, responses={422: {"model": ErrorResponse}})
async def list_documents(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db)) -> PaginatedDocuments:
    """List documents with pagination."""
    if skip < 0 or limit < 1:
        raise ValidationError("Invalid pagination parameters", {"skip": skip, "limit": limit})

    limit = min(limit, 100)

    # Get total count
    count_stmt = select(func.count(Document.id))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar()

    # Get paginated results
    stmt = select(Document).order_by(Document.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    items = [DocumentOut.model_validate(row, from_attributes=True) for row in rows]

    return PaginatedDocuments(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
        has_more=total > (skip + limit),
    )
