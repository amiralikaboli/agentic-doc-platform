import enum
import uuid
from typing import List, Dict, Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    message: str
    details: Dict[str, Any]


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str
    size: int
    status: DocumentStatus


class PaginatedDocuments(BaseModel):
    items: List[DocumentOut]
    total: int
    skip: int
    limit: int
    has_more: bool
