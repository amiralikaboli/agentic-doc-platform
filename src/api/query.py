import time

from fastapi import Depends

from src.api import app
from src.db import search_similar_chunks, SessionLocal
from src.embedding import embedder, rerank
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
    chunk_results = [
        ChunkResult.from_chunk_model(chunk)
        for chunk, _ in search_similar_chunks(db=db, query_vector=query_vector, top_k=2 * paylod.top_k)
    ]

    ranked_chunks = rerank(query=paylod.query, candidates=chunk_results, top_k=paylod.top_k)

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    return QueryResponse(
        query=paylod.query,
        results=ranked_chunks,
        latency_ms=round(elapsed_ms, 2)
    )
