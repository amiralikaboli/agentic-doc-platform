from unittest.mock import patch, AsyncMock

import pytest
from httpx import AsyncClient

from src.api.protos import retrieval_pb2


@pytest.mark.asyncio
async def test_query_endpoint_calls_grpc(async_client: AsyncClient):
    """BB8 DoD: REST endpoint calls gRPC client without changing user-facing behavior."""
    mock_grpc_response = retrieval_pb2.SearchResponse(
        results=[
            retrieval_pb2.SearchResult(
                chunk_id="chunk-1",
                text="HNSW is used in pgvector.",
                score=0.92
            )
        ]
    )

    # Patch the gRPC stub call in your query endpoint logic
    with patch("src.api.query.retrieval_stub.Search", new_callable=AsyncMock) as mock_grpc_search:
        mock_grpc_search.return_value = mock_grpc_response

        payload = {"query": "What is HNSW?", "top_k": 1, "use_hybrid": True}
        response = await async_client.post("/v1/query", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Verify gRPC was called
        mock_grpc_search.assert_called_once()

        # Verify REST payload matches gRPC mapped output
        assert len(data["results"]) == 1
        assert data["results"][0]["chunk_id"] == "chunk-1"