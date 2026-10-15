"""Adaptation proposal cards (Try / Make default / No / Don't suggest again) and the log."""

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.kernel.planner import Block

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
    session_id: str | None = None
    plan_blocks: list[Block] = Field(default_factory=list)
    protected_blocks: int = 0
    plan_state: Literal["ready", "stale", "ended", "superseded"] | None = None


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
    plan_state: Literal["ready", "stale", "ended", "superseded"] | None = None


class HistoryList(BaseModel):
    entries: list[HistoryOut]
