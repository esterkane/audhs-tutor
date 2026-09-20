from typing import Any, Literal

from pydantic import BaseModel, Field


class TurnRequest(BaseModel):
    session_id: str
    text: str = Field(min_length=1, max_length=4000)
    skill_id: str | None = None
    action: Literal["auto", "explain", "hint", "summarize", "full_solution"] = "auto"
    representation: str | None = None


class SourceRef(BaseModel):
    chunk_id: str
    citation: str
    trust_tier: int
    score: float
    flagged: list[str] = Field(default_factory=list)
    cited: bool = False


class TurnMeta(BaseModel):
    turn_id: str
    session_id: str
    skill_id: str
    skill_title: str
    action: str
    hint_level: int
    prompt_version: str
    questioning_style: str
    experiment_arm: str | None = None
    arm_not_applied: bool = False  # the arm's representation was outside the mastery gate


class TurnDone(BaseModel):
    turn_id: str
    model_call_id: str | None
    tutor_trace_id: str
    registry_id: str | None
    route: str | None
    sentences: int
    representation: str | None
    sources: list[SourceRef]
    flagged: list[str]
    dropped: list[str]
    latency_ms: int
    text: str


class SkillView(BaseModel):
    id: str
    slug: str
    title: str
    description: str
    domain: str
    success_criteria: list[str]
    prerequisites: list[str]
    mastery: float
    unlocked: bool
    state: dict[str, Any]
