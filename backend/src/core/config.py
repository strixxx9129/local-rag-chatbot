# backend/src/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "LocalRAGChatbot"
    app_env: str = "development"
    app_debug: bool = False
    secret_key: str
    api_prefix: str = "/api/v1"

    # Database
    database_url: str
    database_url_sync: str

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3:8b"
    ollama_embed_model: str = "nomic-embed-text"
    ollama_embed_dimensions: int = 768

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # File Upload
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 50

    # RAG
    chunk_size: int = 512
    chunk_overlap: int = 64
    retriever_top_k: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()