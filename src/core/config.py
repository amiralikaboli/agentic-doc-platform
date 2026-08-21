"""Configuration management with environment variable support."""
from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Project
    PROJECT_NAME: str = "Agentic Document Intelligence Platform"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Database
    DB_URL: str = os.getenv(
        "DB_URL",
        "postgresql+asyncpg://postgres:postgrespassword@localhost:5432/rag_db"
    )
    DB_ECHO: bool = os.getenv("DB_ECHO", "false").lower() == "true"
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "20"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))

    # Redis (Celery broker & backend)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_SOCKET_TIMEOUT: int = int(os.getenv("REDIS_SOCKET_TIMEOUT", "5"))

    # gRPC Configuration
    GRPC_SERVER_ADDRESS: str = os.getenv("GRPC_SERVER_ADDRESS", "localhost:50051")
    GRPC_PORT: int = int(os.getenv("GRPC_PORT", "50051"))
    GRPC_MAX_WORKERS: int = int(os.getenv("GRPC_MAX_WORKERS", "10"))
    GRPC_REQUEST_TIMEOUT: int = int(os.getenv("GRPC_REQUEST_TIMEOUT", "30"))

    # FastAPI
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_WORKERS: int = int(os.getenv("API_WORKERS", "4"))
    API_RELOAD: bool = os.getenv("API_RELOAD", "false").lower() == "true"

    # Celery
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)
    CELERY_TASK_TIMEOUT: int = int(os.getenv("CELERY_TASK_TIMEOUT", "600"))
    CELERY_TASK_TRACK_STARTED: bool = os.getenv("CELERY_TASK_TRACK_STARTED", "true").lower() == "true"

    # Embedding Model
    EMBEDDING_MODEL_NAME: str = os.getenv(
        "EMBEDDING_MODEL_NAME",
        "sentence-transformers/all-MiniLM-L6-v2"
    )
    EMBEDDING_MODEL_DEVICE: str = os.getenv("EMBEDDING_MODEL_DEVICE", "cpu")
    EMBEDDING_NORMALIZE: bool = os.getenv("EMBEDDING_NORMALIZE", "true").lower() == "true"
    EMBEDDING_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))

    # Reranker Model
    RERANKER_MODEL_NAME: str = os.getenv(
        "RERANKER_MODEL_NAME",
        "BAAI/bge-reranker-base"
    )
    RERANKER_MODEL_DEVICE: str = os.getenv("RERANKER_MODEL_DEVICE", "cpu")
    RERANKER_BATCH_SIZE: int = int(os.getenv("RERANKER_BATCH_SIZE", "32"))

    # Text Chunking
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "512"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))

    # Vector Search
    VECTOR_SEARCH_TOP_K: int = int(os.getenv("VECTOR_SEARCH_TOP_K", "20"))
    VECTOR_SEARCH_RERANK_MULTIPLIER: int = int(os.getenv("VECTOR_SEARCH_RERANK_MULTIPLIER", "2"))

    # File Storage
    DOCUMENT_STORAGE_PATH: str = os.getenv("DOCUMENT_STORAGE_PATH", "data")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "100"))

    # Model Cache
    HF_CACHE_DIR: str = os.getenv("HF_CACHE_DIR", "/app/.cache/huggingface")
    HF_HOME: str = os.getenv("HF_HOME", "/app/.cache/huggingface")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv(
        "LOG_FORMAT",
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
