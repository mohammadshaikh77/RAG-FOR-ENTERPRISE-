from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for Cite platform services."""

    # Application
    app_name: str = "Cite - Enterprise Agentic RAG Platform"
    app_version: str = "0.1.0"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    port: int = Field(default=8000, alias="PORT")

    # PostgreSQL Database
    postgres_user: str = Field(default="cite_user", alias="POSTGRES_USER")
    postgres_password: str = Field(default="cite_password", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="cite_db", alias="POSTGRES_DB")
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    database_url: str = Field(
        default="postgresql+asyncpg://cite_user:cite_password@localhost:5432/cite_db",
        alias="DATABASE_URL",
    )

    # Redis Cache & Queue
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # JWT Authentication
    jwt_secret_key: str = Field(
        default="change-this-to-a-secure-random-32-byte-hex-in-production",
        alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    # LLM Providers
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="openai/gpt-oss-120b", alias="GROQ_MODEL")

    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")

    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.1:8b", alias="OLLAMA_MODEL")

    llm_provider_order_raw: str = Field(default="groq,gemini", alias="LLM_PROVIDER_ORDER")

    # Embedding & Reranker
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", alias="EMBEDDING_MODEL"
    )
    embedding_dimension: int = Field(default=384, alias="EMBEDDING_DIMENSION")
    enable_reranker: bool = Field(default=True, alias="ENABLE_RERANKER")
    reranker_model: str = Field(
        default="cross-encoder/ms-marco-TinyBERT-L-2-v2", alias="RERANKER_MODEL"
    )

    # Multimodal Vision Settings
    multimodal_enabled: bool = Field(default=False, alias="MULTIMODAL_ENABLED")
    multimodal_max_images_per_doc: int = Field(default=10, alias="MULTIMODAL_MAX_IMAGES_PER_DOC")
    multimodal_min_dimension: int = Field(default=150, alias="MULTIMODAL_MIN_DIMENSION")

    # Rate Limiting
    rate_limit_groq_rpm: int = Field(default=25, alias="RATE_LIMIT_GROQ_RPM")
    rate_limit_gemini_rpm: int = Field(default=12, alias="RATE_LIMIT_GEMINI_RPM")
    rate_limit_per_user_rpm: int = Field(default=30, alias="RATE_LIMIT_PER_USER_RPM")

    @property
    def llm_provider_order(self) -> list[str]:
        return [p.strip().lower() for p in self.llm_provider_order_raw.split(",") if p.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
