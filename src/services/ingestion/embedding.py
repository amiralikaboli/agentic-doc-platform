from typing import List

from src.core.models import get_model_manager


class EmbeddingService:
    """Embedding service — delegates to global ModelManager."""

    def __init__(self):
        self.manager = get_model_manager()

    def embed(self, input: str | List[str]):
        return self.manager.embedder.encode(input)
