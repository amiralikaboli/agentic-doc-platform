import uuid
from typing import List

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field()
    top_k: int = Field(default=3, ge=1, le=20)


class ChunkResult(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    content: str
    chunk_index: int
    score: float


class QueryResponse(BaseModel):
    answer: str
    results: List[ChunkResult]
