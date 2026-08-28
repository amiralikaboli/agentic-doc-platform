import os

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Project
    PROJECT_NAME: str = "Agentic Document Intelligence Platform"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Database
    DB_URL: str = os.getenv(
        "DB_URL",
        "postgresql+asyncpg://postgres:postgrespassword@localhost:5432/rag_db"
    )
    DB_NAME: str = os.getenv("DB_NAME", "rag_db")

    # Redis (Celery broker & backend)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # gRPC Configuration
    GRPC_SERVER_ADDRESS: str = os.getenv("GRPC_SERVER_ADDRESS", "localhost:50051")
    GRPC_PORT: int = int(os.getenv("GRPC_PORT", "50051"))
    GRPC_MAX_WORKERS: int = int(os.getenv("GRPC_MAX_WORKERS", "10"))
    GRPC_REQUEST_TIMEOUT: int = int(os.getenv("GRPC_REQUEST_TIMEOUT", "30"))

    # FastAPI
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    # Embedding Model
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
    EMBEDDING_MODEL_DIMENSION: int = int(os.getenv("EMBEDDING_MODEL_DIMENSION", "384"))

    # Reranker Model
    RERANKER_MODEL_NAME: str = os.getenv("RERANKER_MODEL_NAME", "BAAI/bge-reranker-base")

    # File Storage
    DOCUMENT_STORAGE_PATH: str = os.getenv("DOCUMENT_STORAGE_PATH", "data")

    # Model Cache
    HF_CACHE_DIR: str = os.getenv("HF_CACHE_DIR", "/app/.cache/huggingface")
    HF_HOME: str = os.getenv("HF_HOME", "/app/.cache/huggingface")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv(
        "LOG_FORMAT",
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()
