import uuid
from typing import List

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field()
    top_k: int = Field(default=3)


class ChunkResult(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    content: str
    chunk_index: int
    score: float


class QueryResponse(BaseModel):
    results: List[ChunkResult]
    search_time_ms: float
