import logging

import grpc
from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from src.apps.public_api.grpc_client import get_retrieval_client
from src.apps.public_api.schemas.query import QueryRequest, QueryResponse, ChunkResult
from src.core.errors import ExternalServiceError, ValidationError
from src.services.llm import get_llm_client, build_rag_messages

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Query"])

llm_client = get_llm_client()


@router.post("/query", response_model=QueryResponse)
async def query(payload: QueryRequest) -> QueryResponse:
    if not payload.query or not payload.query.strip():
        raise ValidationError("Query cannot be empty")

    client = get_retrieval_client()
    try:
        resp = await run_in_threadpool(client.search, payload.query, payload.top_k)
    except grpc.RpcError as e:
        code = e.code()
        if code == grpc.StatusCode.DEADLINE_EXCEEDED:
            raise ExternalServiceError(
                "Retrieval Service",
                "Request timed out",
                {"grpc_code": str(code)},
            )
        logger.error(f"gRPC error: {code} - {e.details()}")
        raise ExternalServiceError(
            "Retrieval Service",
            "Service unavailable",
            {"grpc_code": str(code)},
        )
    except Exception as e:
        logger.error(f"Unexpected error querying retrieval service: {e}")
        raise ExternalServiceError("Retrieval Service", str(e))

    try:
        chunk_contents = [retrieved_chunk.content for retrieved_chunk in resp.results]
        messages = build_rag_messages(payload.query, chunk_contents)
        answer = await run_in_threadpool(llm_client.generate, messages)
    except ExternalServiceError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating answer: {e}")
        raise ExternalServiceError("LLM Service", str(e))

    return QueryResponse(
        answer=answer,
        results=[
            ChunkResult(
                id=retrieved_chunk.id,
                document_id=retrieved_chunk.document_id,
                content=retrieved_chunk.content,
                chunk_index=retrieved_chunk.chunk_index,
                score=retrieved_chunk.score,
            )
            for retrieved_chunk in resp.results
        ]
    )
