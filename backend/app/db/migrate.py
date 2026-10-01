"""Run Alembic programmatically (app startup in dev, tests, scripts)."""

from pathlib import Path

from alembic.config import Config

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parents[2]


def alembic_config(sync_url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", sync_url)
    return cfg


def upgrade_to_head(sync_url: str) -> None:
    Path(sync_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    command.upgrade(alembic_config(sync_url), "head")
