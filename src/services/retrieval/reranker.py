"""Reranking service using ModelManager."""
from src.core.models import get_model_manager
from src.db.models import Chunk


class RerankerService:
    """Reranker service — delegates to global ModelManager."""

    def __init__(self):
        self.manager = get_model_manager()

    def rerank(self, query: str, candidates: list[Chunk], top_k: int = 5) -> list[tuple[Chunk, float]]:
        """
        Rerank Chunk objects by relevance to query.

        Args:
            query: The search query.
            candidates: List of Chunk objects to rerank.
            top_k: Return top k results.

        Returns:
            List of (Chunk, score) tuples, sorted by score descending.
        """
        if not candidates:
            return []

        pairs = [[query, chunk.content] for chunk in candidates]
        scores = self.manager.reranker.predict(pairs)
        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]
