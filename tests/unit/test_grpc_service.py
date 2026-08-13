from unittest.mock import AsyncMock, patch

import grpc
import pytest

from src.api.protos import retrieval_pb2
from src.api.protos.retrieval_server import RetrievalServicer


@pytest.mark.asyncio
async def test_grpc_search_rpc():
    """BB8 DoD: Tests the gRPC servicer logic independently of the REST API."""
    servicer = RetrievalServicer()

    request = retrieval_pb2.SearchRequest(
        query="Vector DB performance",
        top_k=2,
        use_hybrid=True
    )
    context = AsyncMock(spec=grpc.aio.ServicerContext)

    # Mock the internal DB logic called by the servicer
    with patch.object(servicer, "_perform_hybrid_search") as mock_search:
        mock_search.return_value = [
            {"chunk_id": "c99", "text": "pgvector supports HNSW", "score": 0.88}
        ]

        response = await servicer.Search(request, context)

        assert isinstance(response, retrieval_pb2.SearchResponse)
        assert len(response.results) == 1
        assert response.results[0].chunk_id == "c99"
        assert response.results[0].score == pytest.approx(0.88)
