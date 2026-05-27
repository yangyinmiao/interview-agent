from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "Interview Agent"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://agent:agent123@localhost:5432/interview_agent"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "chunks"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "interview-files"
    minio_secure: bool = False

    # JWT
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    # LLM - OpenAI-compatible API
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model_id: str = "gpt-4o"
    llm_api_key: str = ""
    llm_temperature: float = 0.7
    llm_small_model_id: str = "gpt-4o-mini"

    # Embedding - OpenAI-compatible API
    embedding_base_url: str = "https://api.openai.com/v1"
    embedding_model_id: str = "text-embedding-3-large"
    embedding_api_key: str = ""
    embedding_dimension: int = 3072  # vector dimension for Qdrant collections

    # CORS
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Interview defaults
    max_interview_rounds: int = 10

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
