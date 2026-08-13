import pytest
from src.db import rerank_results


def test_cross_encoder_reranking_direct():
    """BB7 DoD: Validates reranking directly on dense vector candidate results."""
    query = "How does HNSW work?"

    # Candidates returned directly from pgvector dense retrieval
    dense_candidates = [
        {"chunk_id": "c1", "text": "HNSW is a graph-based vector index.", "score": 0.65},
        {"chunk_id": "c2", "text": "Trees are green and produce oxygen.", "score": 0.88}
        # High vector score, wrong semantic meaning
    ]

    # Mock Cross-Encoder scoring
    def mock_predict(pairs):
        return [0.95 if "vector index" in pair[1] else 0.05 for pair in pairs]

    reranked = rerank_results(query, dense_candidates, mock_predict, top_n=1)

    assert len(reranked) == 1
    assert reranked[0]["chunk_id"] == "c1"