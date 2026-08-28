import enum
import uuid
from datetime import datetime
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
    created_at: datetime


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"
    UNKNOWN = "unknown"

    @staticmethod
    def map_task_state(task_state, task_result):
        match task_state:
            case "PENDING":
                return DocumentStatus.UPLOADED, None
            case "STARTED":
                return DocumentStatus.PROCESSING, None
            case "SUCCESS":
                return DocumentStatus.DONE, None
            case "FAILURE":
                return DocumentStatus.FAILED, str(task_result)
        return DocumentStatus.UNKNOWN, None


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
