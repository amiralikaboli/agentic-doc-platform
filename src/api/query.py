import grpc

from src.api import app, APIError
from src.api.protos import retrieval_pb2
from src.models import QueryRequest, QueryResponse, ChunkResult


@app.post("/v1/query", response_model=QueryResponse)
def query(payload: QueryRequest) -> QueryResponse:
    try:
        resp = app.state.grpc_stub.Search(
            retrieval_pb2.SearchRequest(query=payload.query, top_k=payload.top_k),
            timeout=5.0
        )
    except grpc.RpcError as e:
        code = e.code()
        if code == grpc.StatusCode.DEADLINE_EXCEEDED:
            raise APIError(504, "Retrieval service timed out")
        raise APIError(502, "Retrieval service unavailable", {"grpc_code": str(code)})

    return QueryResponse(
        results=[
            ChunkResult(
                id=retrieved_chunk.id,
                document_id=retrieved_chunk.document_id,
                content=retrieved_chunk.content,
                chunk_index=retrieved_chunk.chunk_index,
                score=retrieved_chunk.score
            )
            for retrieved_chunk in resp.results
        ],
        search_time_ms=resp.search_time_ms
    )
