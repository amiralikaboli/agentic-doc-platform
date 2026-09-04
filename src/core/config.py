from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Project
    PROJECT_NAME: str = "Agentic Document Intelligence Platform"

    # Database
    DB_URL: str = "postgresql+asyncpg://postgres:postgrespassword@localhost:5432/rag_db"
    DB_NAME: str = "rag_db"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    # Redis (Celery broker & backend)
    REDIS_URL: str = "redis://localhost:6379/0"

    # gRPC Configuration
    GRPC_SERVER_ADDRESS: str = "localhost:50051"
    GRPC_PORT: int = 50051
    GRPC_MAX_WORKERS: int = 10
    GRPC_REQUEST_TIMEOUT: int = 30

    # FastAPI
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Embedding Model
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_MODEL_DIMENSION: int = 384

    # Reranker Model
    RERANKER_MODEL_NAME: str = "BAAI/bge-reranker-base"

    # LLM Generation (vLLM OpenAI-compatible server)
    LLM_BACKEND: str = "mock"  # "mock" (no GPU needed) | "vllm"
    LLM_BASE_URL: str = "http://localhost:8001/v1"
    LLM_MODEL_NAME: str = "Qwen/Qwen2.5-7B-Instruct"
    LLM_API_KEY: str = "not-needed"
    LLM_MAX_TOKENS: int = 512
    LLM_TEMPERATURE: float = 0.2
    LLM_REQUEST_TIMEOUT: int = 60

    # File Storage
    DOCUMENT_STORAGE_PATH: str = "data"

    # Model Cache
    HF_CACHE_DIR: str = "/app/.cache/huggingface"
    HF_HOME: str = "/app/.cache/huggingface"

    # Logging

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()
