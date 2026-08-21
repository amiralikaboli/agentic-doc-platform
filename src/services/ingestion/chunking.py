"""Text chunking service using ModelManager."""
from src.core.models import get_model_manager


class ChunkingService:
    """Chunking service — delegates to global ModelManager."""

    def __init__(self):
        self.manager = get_model_manager()

    def split_text(self, text: str) -> list[str]:
        """Split text into semantic chunks."""
        return self.manager.chunker.split_text(text)
