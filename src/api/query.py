import time

from fastapi import Depends

from src.api import app
from src.db import search_similar_chunks, SessionLocal
from src.embedding import embedder
from src.models import QueryRequest, ChunkResult, QueryResponse


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/v1/query", response_model=QueryResponse)
def query(paylod: QueryRequest, db=Depends(get_db)) -> QueryResponse:
    start_time = time.perf_counter()

    query_vector = embedder.embed_query(paylod.query)

    search_results = search_similar_chunks(db=db, query_vector=query_vector, top_k=paylod.top_k)

    chunk_results = [
        ChunkResult(
            id=chunk.id,
            document_id=chunk.document_id,
            content=chunk.content,
            chunk_index=chunk.chunk_index,
            distance=distance
        )
        for chunk, distance in search_results
    ]

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    return QueryResponse(
        query=paylod.query,
        results=chunk_results,
        latency_ms=round(elapsed_ms, 2)
    )
