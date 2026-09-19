"""Application settings. The only place configuration is read (CLAUDE.md: never elsewhere)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    app_env: str = "dev"
    database_url: str = "sqlite+aiosqlite:///./data/dev.db"
    ollama_host: str = "http://localhost:11434"
    anthropic_api_key: str = ""
    daily_budget_usd: float = 1.50
    routing_profile: str = "default"
    embed_model: str = "nomic-embed-text"
    whisper_model: str = "mlx-community/whisper-large-v3-turbo"
    kokoro_url: str = "http://localhost:8880"
    qdrant_url: str = "http://localhost:6333"
    models_dir: str = "./data/models"
    hf_token: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
