import logging

from sentence_transformers import SentenceTransformer, CrossEncoder

from src.core.config import settings

logger = logging.getLogger(__name__)


class ModelManager:
    _instance: "ModelManager | None" = None
    _embedder: SentenceTransformer | None = None
    _reranker: CrossEncoder | None = None

    def __new__(cls) -> "ModelManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize_for_retrieval(self) -> None:
        logger.info("Initializing ModelManager for retrieval service (embedder + reranker)...")
        try:
            self._load_embedder()
            self._load_reranker()
            logger.info("✓ Retrieval service models initialized")
        except Exception as e:
            logger.error(f"Failed to initialize retrieval models: {e}")
            raise

    def initialize_for_worker(self) -> None:
        logger.info("Initializing ModelManager for worker (embedder)...")
        try:
            self._load_embedder()
            logger.info("✓ Worker models initialized")
        except Exception as e:
            logger.error(f"Failed to initialize worker models: {e}")
            raise

    def _load_embedder(self) -> None:
        if self._embedder is not None:
            logger.debug("Embedder already loaded")
            return

        logger.info(f"Loading embedder: {settings.EMBEDDING_MODEL_NAME}...")
        self._embedder = SentenceTransformer(
            settings.EMBEDDING_MODEL_NAME,
            trust_remote_code=True,
        )
        logger.info("✓ Embedder loaded")

    def _load_reranker(self) -> None:
        if self._reranker is not None:
            logger.debug("Reranker already loaded")
            return

        logger.info(f"Loading reranker: {settings.RERANKER_MODEL_NAME}...")
        self._reranker = CrossEncoder(settings.RERANKER_MODEL_NAME)
        logger.info("✓ Reranker loaded")

    @property
    def embedder(self) -> SentenceTransformer:
        if self._embedder is None:
            raise RuntimeError("Embedder not initialized. Call initialize_for_* first.")
        return self._embedder

    @property
    def reranker(self) -> CrossEncoder:
        if self._reranker is None:
            raise RuntimeError("Reranker not initialized. Call initialize_for_* first.")
        return self._reranker


# Global singleton instance
_model_manager = ModelManager()


def get_model_manager() -> ModelManager:
    """Get the global model manager instance."""
    return _model_manager
