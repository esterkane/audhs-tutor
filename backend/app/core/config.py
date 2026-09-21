"""Application settings. The only place configuration is read (CLAUDE.md: never elsewhere).

Relative SQLite paths in DATABASE_URL are resolved against the project root (parent of backend/),
so `./data/dev.db` means `<repo>/data/dev.db` regardless of the current working directory.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(str(PROJECT_ROOT / ".env"), ".env"), extra="ignore")

    app_env: str = "dev"
    database_url: str = "sqlite+aiosqlite:///./data/dev.db"
    auto_migrate: bool = True
    ollama_host: str = "http://localhost:11434"
    anthropic_api_key: str = ""
    daily_budget_usd: float = 1.50
    routing_profile: str = "default"
    embed_model: str = "nomic-embed-text"
    kokoro_url: str = "http://localhost:8880"
    qdrant_url: str = "http://localhost:6333"
    retrieval_max_per_document: int = 3  # diversity cap on hits from one document (0 = off)
    quarantine_below_trust: int = 2  # flagged chunks below this trust tier never reach the tutor
    ingest_roots: str = "~"  # comma-separated folders the ingest API may read (CLI is unrestricted)
    transcript_cache_dir: str = "./data/transcripts"  # STT results by content hash
    stt_language: str = ""  # ISO code forced for transcription; empty = auto-detect
    voice_dir: str = "./data/voice"  # retained voice recordings (opt-in, see voice.retain_audio)

    @property
    def ingest_roots_resolved(self) -> list[Path]:
        return [
            Path(r.strip()).expanduser().resolve()
            for r in self.ingest_roots.split(",")
            if r.strip()
        ]

    models_dir: str = "./data/models"
    hf_token: str = ""

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    def _resolve_sqlite(self, url: str) -> str:
        marker = ":///./"
        if marker in url:
            scheme, rel = url.split(":///./", 1)
            return f"{scheme}:///{(PROJECT_ROOT / rel).resolve()}"
        return url

    @property
    def database_url_resolved(self) -> str:
        return self._resolve_sqlite(self.database_url)

    @property
    def sync_database_url(self) -> str:
        return self.database_url_resolved.replace("+aiosqlite", "")

    @property
    def models_dir_resolved(self) -> Path:
        p = Path(self.models_dir)
        return p if p.is_absolute() else (PROJECT_ROOT / p).resolve()

    @property
    def voice_dir_resolved(self) -> Path:
        p = Path(self.voice_dir).expanduser()
        return p if p.is_absolute() else (PROJECT_ROOT / p).resolve()

    @property
    def transcript_cache_dir_resolved(self) -> Path:
        p = Path(self.transcript_cache_dir).expanduser()
        return p if p.is_absolute() else (PROJECT_ROOT / p).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
