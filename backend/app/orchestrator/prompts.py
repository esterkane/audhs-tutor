"""Versioned prompt files (prompts/). The base policy is the byte-stable cached prefix."""

from functools import lru_cache
from pathlib import Path

from app.core.config import PROJECT_ROOT

PROMPTS_DIR = PROJECT_ROOT / "prompts"
BASE_VERSION = "pedagogy.v2"
TUTOR_VERSION = "tutor.v1"
GRADER_VERSION = "grader.explain_back.v1"
CURRICULUM_VERSION = "curriculum.draft.v2"
LISTENING_VERSION = "listening.comprehension.v1"
VOICE_VERSION = "voice.conversation.v1"
PROMPT_VERSION = f"{BASE_VERSION}+{TUTOR_VERSION}"


@lru_cache
def _read(rel: str) -> str:
    path: Path = PROMPTS_DIR / rel
    return path.read_text()


def base_policy() -> str:
    """Byte-stable system prompt. Never add timestamps or per-turn data here (prompt caching)."""
    return _read(f"_base/{BASE_VERSION}.md")


def tutor_task(name: str) -> str:
    return _read(f"tutor/{name}.v1.md")


def grader_task(name: str) -> str:
    return _read(f"grader/{name}.v1.md")


def challenge_task(mode: str) -> str:
    return _read(f"challenge/{mode}.v1.md")


def curriculum_task(name: str) -> str:
    return _read(f"curriculum/{name}.v2.md")


def listening_task(name: str) -> str:
    return _read(f"listening/{name}.v1.md")


def voice_task(name: str) -> str:
    return _read(f"voice/{name}.v1.md")


def playground_task() -> str:
    return _read("playground/tutor.v1.md")
