import os
import shutil
import uuid
from typing import Dict

from fastapi import UploadFile, Header, Response

from src.api import app, APIError
from src.celery_app import celery_app
from src.models import ErrorResponse, DocumentOut, DocumentStatusOut, PaginatedDocuments, DocumentStatus
from src.tasks import process_document_task

id2document: Dict[uuid.UUID, DocumentOut] = {}
idempotency_store: Dict[str, uuid.UUID] = {}


@app.post("/v1/documents", status_code=202, response_model=DocumentOut, responses={422: {"model": ErrorResponse}})
def create_document(
        response: Response,
        file: UploadFile,
        idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> DocumentOut:
    if idempotency_key and idempotency_key in idempotency_store:
        existing_id = idempotency_store[idempotency_key]
        response.headers["Location"] = f"/v1/documents/{existing_id}"
        return id2document[existing_id]

    doc_id = uuid.uuid4()

    dest_path = f"data/{doc_id}"
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    document = DocumentOut(
        id=doc_id,
        filename=file.filename,
        content_type=file.content_type,
        size=os.path.getsize(dest_path)
    )
    id2document[doc_id] = document

    task = process_document_task.delay(str(doc_id))
    document.task_id = task.id

    if idempotency_key:
        idempotency_store[idempotency_key] = doc_id

    response.headers["Location"] = f"/v1/documents/{doc_id}"
    return document


@app.get("/v1/documents/{id}", response_model=DocumentOut, responses={404: {"model": ErrorResponse}})
def get_document(id: uuid.UUID) -> DocumentOut:
    if id not in id2document:
        raise APIError(status_code=404, message="Document not found")
    return id2document[id]


@app.get("/v1/documents/{id}/status", response_model=DocumentStatusOut, responses={404: {"model": ErrorResponse}})
def get_document_status(id: uuid.UUID) -> DocumentStatusOut:
    if id not in id2document:
        raise APIError(status_code=404, message="Document not found")

    document = id2document[id]
    task = celery_app.AsyncResult(document.task_id)

    status, error_reason = DocumentStatus.map_task_state(task.state, task.result)

    return DocumentStatusOut(
        id=document.id,
        status=status,
        error_reason=error_reason
    )


@app.get("/v1/documents", response_model=PaginatedDocuments, responses={422: {"model": ErrorResponse}})
def list_document(skip: int = 0, limit: int = 10) -> PaginatedDocuments:
    if skip < 0 or limit < 1:
        raise APIError(status_code=422, message="Invalid pagination parameters")

    all_docs = list(id2document.values())
    limit = min(limit, 100)

    return PaginatedDocuments(
        items=all_docs[skip: skip + limit],
        total=len(all_docs),
        skip=skip,
        limit=limit,
        has_more=len(all_docs) > (skip + limit)
    )
