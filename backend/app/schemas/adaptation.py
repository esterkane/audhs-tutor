"""Adaptation proposal cards (Try / Make default / No / Don't suggest again) and the log."""

from typing import Any, Literal

from pydantic import BaseModel

Decision = Literal["try", "default", "no", "never"]


class ProposalOut(BaseModel):
    id: str
    what: str
    why: str
    origin: str
    pattern: str
    pref: str
    value: Any
    evidence: dict[str, Any]
    proposed_at: str
    reversible: bool


class ProposalList(BaseModel):
    proposals: list[ProposalOut]


class DecideIn(BaseModel):
    decision: Decision
    session_id: str | None = None


class HistoryOut(BaseModel):
    id: str
    what: str
    why: str
    origin: str
    pattern: str
    pref: str
    value: Any
    previous: Any | None
    proposed_at: str
    decision: str | None
    decided_at: str | None
    undone_at: str | None
    in_effect: bool
    trial: bool


class HistoryList(BaseModel):
    entries: list[HistoryOut]
