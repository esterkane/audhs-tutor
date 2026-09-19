"""Teaching-action choice (ADR-0003): hint ladder, explicit full-solution opt-in, no silent mode switch."""

import re
from enum import StrEnum
from typing import Any

from app.orchestrator import prompts

MAX_HINT_LEVEL = 3
FULL_SOLUTION_PATTERNS = re.compile(
    r"show (me )?the full solution|full solution|show (me )?the (complete|whole) solution", re.I
)
NEGATED_FULL_SOLUTION = re.compile(
    r"\b(don'?t|do not|not|without|no|never)\b[^.!?]{0,25}(full|complete|whole) solution", re.I
)
HINT_PATTERNS = re.compile(r"\bhint\b|\bstuck\b|\bnudge\b|\bnext step\b|where do i start", re.I)
SUMMARY_PATTERNS = re.compile(r"\bsummar(y|ise|ize)\b|\brecap\b", re.I)


class Action(StrEnum):
    EXPLAIN = "explain"
    HINT = "hint"
    FULL_SOLUTION = "full_solution"
    SUMMARIZE = "summarize"


def choose_action(text: str, requested: str, hint_level: int) -> tuple[Action, int]:
    """Returns (action, hint_level). Full solution only on an explicit request or button."""
    if requested == "full_solution":
        return Action.FULL_SOLUTION, hint_level
    if (
        requested == "auto"
        and FULL_SOLUTION_PATTERNS.search(text)
        and not NEGATED_FULL_SOLUTION.search(text)
    ):
        return Action.FULL_SOLUTION, hint_level
    if requested == "hint" or (requested == "auto" and HINT_PATTERNS.search(text)):
        return Action.HINT, min(MAX_HINT_LEVEL, hint_level + 1)
    if requested == "summarize" or (requested == "auto" and SUMMARY_PATTERNS.search(text)):
        return Action.SUMMARIZE, hint_level
    return Action.EXPLAIN, hint_level


SCAFFOLD_PROBLEM_FIRST_MIN_MASTERY = 0.6


def output_contract(
    action: Action,
    *,
    hint_level: int,
    socratic: bool,
    representation: str | None,
    block_type: str,
    mastery: float = 0.0,
) -> dict[str, Any]:
    style = "socratic" if socratic else "explicit"
    contract: dict[str, Any] = {
        "action": str(action),
        "questioning_style": style,
        "block_type": block_type,
        "max_sentences": {"hint": 3, "summarize": 5, "explain": 6, "full_solution": 10}[
            str(action)
        ],
        "citation_format": "source number in square brackets, e.g. [1]",
        "representation": representation or "choose one and name it in brackets first",
        "instructions": prompts.tutor_task(str(action)).strip(),
    }
    contract["shape_example"] = (
        "(analogy) One or two short sentences that answer the request, grounded in source [1]. "
        "Next: one concrete step."
    )
    contract["scaffold"] = (
        "worked_example_first"
        if mastery < SCAFFOLD_PROBLEM_FIRST_MIN_MASTERY
        else "problem_first_allowed"
    )
    if socratic:
        contract["socratic_rule"] = (
            "no explanation; at most 2 sentences of setup, then exactly one narrowing question"
        )
    if action == Action.HINT:
        contract["hint_level"] = hint_level
    if action == Action.FULL_SOLUTION:
        contract["end_with"] = "exactly one check question"
    else:
        contract["end_with"] = "one concrete next step or 2-3 concrete options"
    return contract


REPRESENTATION_PREFIX = re.compile(
    r"^[\s*_#]*[\(\[]\s*(analogy|derivation|code|diagram(?:-in-words)?|worked example|problem[- ]first|narrative)"
    r"\s*[\)\]]",
    re.I,
)
REPRESENTATION_MAP = {
    "analogy": "analogy",
    "derivation": "derivation",
    "code": "code",
    "diagram": "diagram",
    "diagram-in-words": "diagram",
    "worked example": "worked_example",
    "problem-first": "problem_first",
    "problem first": "problem_first",
    "narrative": "narrative",
}


def detect_representation(text: str) -> str | None:
    m = REPRESENTATION_PREFIX.match(text)
    return REPRESENTATION_MAP.get(m.group(1).lower()) if m else None


def count_sentences(text: str) -> int:
    return len([s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s])


def trim_incomplete_tail(text: str) -> str:
    """If generation stopped mid-sentence (token cap), drop the dangling fragment."""
    t = text.rstrip()
    if not t or t[-1] in ".!?)]\"'":
        return t
    cut = max(
        t.rfind(". "), t.rfind("? "), t.rfind("! "), t.rfind(".\n"), t.rfind("?\n"), t.rfind("!\n")
    )
    return t[: cut + 1] if cut > 40 else t


def cited_indices(text: str, n_sources: int) -> set[int]:
    """Numeric citations actually present in the reply, e.g. [1] or [1, 3]."""
    found: set[int] = set()
    for m in re.finditer(r"\[(\d+(?:\s*,\s*\d+)*)\]", text):
        for part in m.group(1).split(","):
            i = int(part)
            if 1 <= i <= n_sources:
                found.add(i)
    return found
