from typing import List

import numpy as np
from numpy.typing import NDArray

from src.core.models import get_model_manager


class EmbeddingService:
    """Embedding service — delegates to global ModelManager."""

    def __init__(self):
        self.manager = get_model_manager()

    def embed(self, input: str | List[str]) -> NDArray[np.float32]:
        return self.manager.embedder.encode(input)
