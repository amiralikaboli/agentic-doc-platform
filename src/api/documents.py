import os
import shutil
import uuid

from fastapi import UploadFile, Header, Response
from fastapi.params import Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api import app, APIError
from src.celery_app import celery_app
from src.db import DocumentModel, SessionLocal, ChunkModel
from src.models import ErrorResponse, DocumentOut, DocumentStatusOut, PaginatedDocuments, DocumentStatus
from src.tasks import process_document_task


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/v1/documents", status_code=202, response_model=DocumentOut, responses={422: {"model": ErrorResponse}})
def create_document(
        response: Response,
        file: UploadFile,
        idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
        db: Session = Depends(get_db)
) -> DocumentOut:
    if idempotency_key:
        existing = db.query(DocumentModel).filter_by(idempotency_key=idempotency_key).first()
        if existing:
            response.headers["Location"] = f"/v1/documents/{existing.id}"
            return DocumentOut.model_validate(existing, from_attributes=True)

    doc_id = uuid.uuid4()

    dest_path = f"data/{doc_id}"
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    record = DocumentModel(
        id=doc_id,
        filename=file.filename,
        content_type=file.content_type,
        size=os.path.getsize(dest_path),
        idempotency_key=idempotency_key
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(DocumentModel).filter_by(idempotency_key=idempotency_key).first()
        response.headers["Location"] = f"/v1/documents/{existing.id}"
        return DocumentOut.model_validate(existing, from_attributes=True)

    task = process_document_task.delay(str(doc_id))
    record.task_id = task.id
    db.commit()

    response.headers["Location"] = f"/v1/documents/{doc_id}"
    return DocumentOut.model_validate(record, from_attributes=True)


@app.get("/v1/documents/{id}", response_model=DocumentOut, responses={404: {"model": ErrorResponse}})
def get_document(id: uuid.UUID, db: Session = Depends(get_db)) -> DocumentOut:
    record = db.query(DocumentModel).filter_by(id=id).first()
    if not record:
        raise APIError(status_code=404, message="Document not found")
    return DocumentOut.model_validate(record, from_attributes=True)


@app.delete("/v1/documents/{id}", status_code=204, responses={404: {"model": ErrorResponse}})
def delete_document(id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    record = db.query(DocumentModel).filter_by(id=id).first()
    if not record:
        raise APIError(status_code=404, message="Document not found")

    if record.task_id:
        celery_app.control.revoke(record.task_id, terminate=True)

    db.query(ChunkModel).filter_by(document_id=id).delete()
    db.delete(record)
    db.commit()

    dest_path = f"data/{id}"
    if os.path.exists(dest_path):
        os.remove(dest_path)

    return Response(status_code=204)


@app.get("/v1/documents/{id}/status", response_model=DocumentStatusOut, responses={404: {"model": ErrorResponse}})
def get_document_status(id: uuid.UUID, db: Session = Depends(get_db)) -> DocumentStatusOut:
    record = db.query(DocumentModel).filter_by(id=id).first()
    if not record:
        raise APIError(status_code=404, message="Document not found")

    task = celery_app.AsyncResult(record.task_id)

    status, error_reason = DocumentStatus.map_task_state(task.state, task.result)

    return DocumentStatusOut(
        id=record.id,
        status=status,
        error_reason=error_reason
    )


@app.get("/v1/documents", response_model=PaginatedDocuments, responses={422: {"model": ErrorResponse}})
def list_document(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)) -> PaginatedDocuments:
    if skip < 0 or limit < 1:
        raise APIError(status_code=422, message="Invalid pagination parameters")

    limit = min(limit, 100)

    total = db.query(DocumentModel).count()
    rows = (
        db.query(DocumentModel)
        .order_by(DocumentModel.id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    items = [DocumentOut.model_validate(row, from_attributes=True) for row in rows]

    return PaginatedDocuments(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
        has_more=total > (skip + limit)
    )
