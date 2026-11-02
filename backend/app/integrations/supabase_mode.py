"""Session mode belongs to the learner, not generated response metadata."""

import re
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import replace
from functools import lru_cache
from typing import Any, Literal, get_args

from pydantic import BaseModel, create_model

_MODE: ContextVar[str | None] = ContextVar("project_selected_mode", default=None)
_NAMES = {
    "lesson": "lesson",
    "learning": "lesson",
    "lernmodus": "lesson",
    "lesson mode": "lesson",
    "incident": "incident",
    "incident mode": "incident",
    "incident-modus": "incident",
    "exam": "exam",
    "exam mode": "exam",
    "prüfungsmodus": "exam",
    "neutral": "neutral",
    "neutral mode": "neutral",
    "neutraler modus": "neutral",
    "neutralen modus": "neutral",
    "rabbit_hole": "rabbit_hole",
    "rabbit hole": "rabbit_hole",
}
_COMMAND = re.compile(
    r"(?:(?:please )?(?:switch to|change to|use|enter) "
    r"|(?:bitte )?(?:wechsle in den|wechsel in den|wechsle zu|wechsel zu|nutze) )?"
    r"(.+?)(?: please| bitte)?[.!]?",
    re.I,
)


def requested_mode(text: str) -> str | None:
    # Only whole directive clauses; quotations, code, negations and ordinary mentions
    # must never become a mode-change command.
    prose = re.sub(r"```.*?(?:```|$)", "", text, flags=re.S)
    choices = []
    for clause in re.split(r"[;\n]", prose):
        match = _COMMAND.fullmatch(clause.strip())
        if match:
            selected = _NAMES.get(match[1].strip().lower())
            if selected:
                choices.append(selected)
    return choices[-1] if choices else None


def standalone_mode(text: str) -> str | None:
    """Only a whole control command, never discard a question, quote or code block."""
    match = _COMMAND.fullmatch(text.strip())
    return _NAMES.get(match[1].strip().lower()) if match else None


def selected_state(state: Any, text: str) -> Any:
    mode = requested_mode(text)
    return replace(state, mode=mode) if mode is not None and mode != state.mode else state


@contextmanager
def mode_scope(state: Any) -> Iterator[None]:
    token = _MODE.set(state.mode)
    try:
        yield
    finally:
        _MODE.reset(token)


@lru_cache
def _mode_schema(base: type[BaseModel], mode: str) -> type[BaseModel]:
    types = [
        kind
        for kind in get_args(base.model_fields["state"].annotation)
        if isinstance(kind, type) and issubclass(kind, BaseModel)
    ]
    if len(types) != 1:
        return base  # Search-only requests have no final state.
    metadata = create_model(
        "SelectedModeMetadata", __base__=types[0], mode=(Literal.__getitem__(mode), mode)
    )
    return create_model("SelectedModeDecision", __base__=base, state=(metadata | None, None))


def mode_schema(base: type[BaseModel]) -> type[BaseModel]:
    mode = _MODE.get()
    return _mode_schema(base, mode) if mode is not None else base
