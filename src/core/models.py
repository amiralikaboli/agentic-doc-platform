"""Model loading and lifecycle management."""
import logging
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_experimental.text_splitter import SemanticChunker
from sentence_transformers import CrossEncoder

from src.core.config import settings

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Singleton model manager — loads models on-demand, once per process during startup.
    
    Each process explicitly initializes only the models it needs:
    - API: initialize_for_api() → embedder only
    - Retrieval service: initialize_for_retrieval() → embedder only
    - Worker: initialize_for_worker() → embedder + chunker
    """

    _instance: "ModelManager | None" = None
    _embedder: HuggingFaceEmbeddings | None = None
    _chunker: SemanticChunker | None = None
    _reranker: CrossEncoder | None = None

    def __new__(cls) -> "ModelManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize_for_retrieval(self) -> None:
        """Initialize models needed for retrieval service (embedder only)."""
        logger.info("Initializing ModelManager for retrieval service (embedder only)...")
        try:
            self._load_embedder()
            logger.info("✓ Retrieval service models initialized")
        except Exception as e:
            logger.error(f"Failed to initialize retrieval models: {e}")
            raise

    def initialize_for_worker(self) -> None:
        """Initialize models needed for worker (embedder + chunker)."""
        logger.info("Initializing ModelManager for worker (embedder + chunker)...")
        try:
            self._load_embedder()
            self._load_chunker()
            logger.info("✓ Worker models initialized")
        except Exception as e:
            logger.error(f"Failed to initialize worker models: {e}")
            raise

    def _load_embedder(self) -> None:
        """Load embedding model."""
        if self._embedder is not None:
            logger.debug("Embedder already loaded")
            return

        logger.info(f"Loading embedder: {settings.EMBEDDING_MODEL_NAME}...")
        self._embedder = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL_NAME,
            model_kwargs={"device": settings.EMBEDDING_MODEL_DEVICE},
            encode_kwargs={"normalize_embeddings": settings.EMBEDDING_NORMALIZE},
        )
        logger.info("✓ Embedder loaded")

    def _load_chunker(self) -> None:
        """Load chunker (requires embedder)."""
        if self._chunker is not None:
            logger.debug("Chunker already loaded")
            return

        if self._embedder is None:
            raise RuntimeError("Embedder must be loaded before chunker")

        logger.info("Loading chunker...")
        self._chunker = SemanticChunker(embeddings=self._embedder)
        logger.info("✓ Chunker loaded")

    def _load_reranker(self) -> None:
        """Load reranker model."""
        if self._reranker is not None:
            logger.debug("Reranker already loaded")
            return

        logger.info(f"Loading reranker: {settings.RERANKER_MODEL_NAME}...")
        self._reranker = CrossEncoder(settings.RERANKER_MODEL_NAME)
        logger.info("✓ Reranker loaded")

    @property
    def embedder(self) -> HuggingFaceEmbeddings:
        """Get embedder instance (must be initialized first)."""
        if self._embedder is None:
            raise RuntimeError("Embedder not initialized. Call initialize_for_* first.")
        return self._embedder

    @property
    def chunker(self) -> SemanticChunker:
        """Get chunker instance (must be initialized first)."""
        if self._chunker is None:
            raise RuntimeError("Chunker not initialized. Call initialize_for_* first.")
        return self._chunker

    @property
    def reranker(self) -> CrossEncoder:
        """Get reranker instance (must be initialized first)."""
        if self._reranker is None:
            raise RuntimeError("Reranker not initialized. Call initialize_for_* first.")
        return self._reranker

    @property
    def is_healthy(self) -> bool:
        """Check if any models are loaded."""
        return any([self._embedder, self._chunker, self._reranker])

    @property
    def has_embedder(self) -> bool:
        """Check if embedder is loaded."""
        return self._embedder is not None

    @property
    def has_chunker(self) -> bool:
        """Check if chunker is loaded."""
        return self._chunker is not None

    @property
    def has_reranker(self) -> bool:
        """Check if reranker is loaded."""
        return self._reranker is not None


# Global singleton instance
_model_manager = ModelManager()


def get_model_manager() -> ModelManager:
    """Get the global model manager instance."""
    return _model_manager
