"""Application configuration via environment variables."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM provider (used in Phase 6)
    llm_provider: str = "mock"  # "mock" | "claude" | "openai" | "ollama"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.1:8b"

    # Vector store
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "eshop_code"
    embedding_model: str = "all-MiniLM-L6-v2"

    # External services (mocks)
    jira_mock_url: str = "http://jira-mock:3100"
    notification_mock_url: str = "http://notification-mock:3200"

    # Observability (Phase 10)
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://langfuse-web:3000"

    # Persistence
    checkpoint_db_path: str = "/app/data/checkpoints/upstream.sqlite"


settings = Settings()
