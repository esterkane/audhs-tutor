"""Read-only evidence provenance; no new competency levels or independence inference."""

from typing import Literal

from pydantic import BaseModel


class ProgressEvidence(BaseModel):
    id: str
    dimension: str
    recorded_at: str
    score: float
    weight: float
    grader_level: str
    attempt_id: str | None
    reported_hint_count: int | None
    independence: Literal["not_verified"] = "not_verified"


class ProgressDimension(BaseModel):
    dimension: str
    count: int
    last_recorded_at: str


class ProgressEvidencePage(BaseModel):
    skill_id: str
    total: int
    offset: int
    limit: int
    items: list[ProgressEvidence]
    dimensions: list[ProgressDimension]
