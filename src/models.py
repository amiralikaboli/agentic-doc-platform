import uuid
from typing import List, Dict, Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    message: str
    details: Dict[str, Any]


class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str
    size: int
    task_id: str | None = Field(None, exclude=True)


class DocumentStatusOut(BaseModel):
    id: uuid.UUID
    status: str
    error_reason: str | None = None


class PaginatedDocuments(BaseModel):
    items: List[DocumentOut]
    total: int
    skip: int
    limit: int
    has_more: bool
