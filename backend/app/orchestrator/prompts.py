"""Versioned prompt files (prompts/). The base policy is the byte-stable cached prefix."""

from functools import lru_cache
from pathlib import Path

from app.core.config import PROJECT_ROOT

PROMPTS_DIR = PROJECT_ROOT / "prompts"
BASE_VERSION = "pedagogy.v1"
TUTOR_VERSION = "tutor.v1"
GRADER_VERSION = "grader.explain_back.v1"
PROMPT_VERSION = f"{BASE_VERSION}+{TUTOR_VERSION}"


@lru_cache
def _read(rel: str) -> str:
    path: Path = PROMPTS_DIR / rel
    return path.read_text()


def base_policy() -> str:
    """Byte-stable system prompt. Never add timestamps or per-turn data here (prompt caching)."""
    return _read("_base/pedagogy.v1.md")


def tutor_task(name: str) -> str:
    return _read(f"tutor/{name}.v1.md")


def grader_task(name: str) -> str:
    return _read(f"grader/{name}.v1.md")


def challenge_task(mode: str) -> str:
    return _read(f"challenge/{mode}.v1.md")
