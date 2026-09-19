"""Teaching-action choice (ADR-0003): hint ladder, explicit full-solution opt-in, no silent mode switch."""

import re
from enum import StrEnum
from typing import Any

from app.orchestrator import prompts

MAX_HINT_LEVEL = 3
FULL_SOLUTION_PATTERNS = re.compile(
    r"show (me )?the full solution|full solution|show (me )?the (complete|whole) solution", re.I
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
    if requested == "full_solution" or FULL_SOLUTION_PATTERNS.search(text):
        return Action.FULL_SOLUTION, hint_level
    if requested == "hint" or (requested == "auto" and HINT_PATTERNS.search(text)):
        return Action.HINT, min(MAX_HINT_LEVEL, hint_level + 1)
    if requested == "summarize" or (requested == "auto" and SUMMARY_PATTERNS.search(text)):
        return Action.SUMMARIZE, hint_level
    return Action.EXPLAIN, hint_level


def output_contract(
    action: Action, *, hint_level: int, socratic: bool, representation: str | None, block_type: str
) -> dict[str, Any]:
    style = "socratic" if socratic else "explicit"
    contract: dict[str, Any] = {
        "action": str(action),
        "questioning_style": style,
        "block_type": block_type,
        "max_sentences": {"hint": 3, "summarize": 5, "explain": 6, "full_solution": 10}[
            str(action)
        ],
        "citation_format": "[course › section › lecture]",
        "representation": representation or "choose one and name it in brackets first",
        "instructions": prompts.tutor_task(str(action)).strip(),
    }
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
