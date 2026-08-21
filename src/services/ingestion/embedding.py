"""Embedding service using ModelManager."""
from src.core.models import get_model_manager


class EmbeddingService:
    """Embedding service — delegates to global ModelManager."""

    def __init__(self):
        self.manager = get_model_manager()

    def embed_text(self, text: str) -> list[float]:
        """Embed a single text query."""
        return self.manager.embedder.embed_query(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts."""
        return self.manager.embedder.embed_documents(texts)
