"""Hard checks for tutoring quality (tutor-eval skill §2). Pure functions; used by evals and benchmarks."""

import re
from typing import Any

from app.orchestrator.actions import count_sentences

BANNED = [
    r"great question", r"learning style", r"visual learner", r"auditory learner", r"how do you feel",
    r"don't worry", r"\bstreak\b", r"awesome job", r"you're doing great", r"well done", r"great job",
    r"nice work", r"you've got this", r"keep it up",
]  # fmt: skip
MAX_SENTENCES = {"explain": 6, "hint": 3, "summarize": 5, "full_solution": 12}


def no_banned_language(text: str) -> bool:
    low = text.lower()
    return not any(re.search(p, low) for p in BANNED)


def citation_present(text: str, sources: list[dict[str, Any]]) -> bool:
    """A citation actually written in the reply ([n] or [course › …]), or an explicit 'no course source'.
    Retrieval hits alone do not count."""
    return bool(re.search(r"\[\d+\]|\[[^\]]+›[^\]]+\]", text)) or "no course source" in text.lower()


def no_full_solution(text: str, forbidden: list[str], action: str) -> bool:
    if action == "full_solution":
        return True
    low = text.lower()
    return not any(f.lower() in low for f in forbidden)


def mode_respected(text: str, questioning_style: str, action: str) -> bool:
    """Explicit mode: explains directly (at most 2 questions). Socratic: ends with one question."""
    questions = text.count("?")
    if questioning_style == "socratic":
        return text.strip().endswith("?") and questions <= 2
    return questions <= 2


def within_sentence_limit(text: str, action: str, limit: int | None = None) -> bool:
    return count_sentences(text) <= (limit or MAX_SENTENCES.get(action, 6))


def run_hard_checks(
    text: str, *, action: str, questioning_style: str, sources: list[dict[str, Any]],
    expect: dict[str, Any] | None = None,
) -> dict[str, bool]:  # fmt: skip
    expect = expect or {}
    checks: dict[str, bool] = {}
    if expect.get("no_full_solution", True):
        checks["no_full_solution"] = no_full_solution(
            text, list(expect.get("forbidden", [])), action
        )
    if expect.get("citation_present", True):
        checks["citation_present"] = citation_present(text, sources)
    checks["max_sentences"] = within_sentence_limit(text, action, expect.get("max_sentences"))
    if expect.get("no_banned_language", True):
        checks["no_banned_language"] = no_banned_language(text)
    if expect.get("mode_respected", True):
        checks["mode_respected"] = mode_respected(text, questioning_style, action)
    return checks
