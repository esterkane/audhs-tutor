"""Read-only evidence provenance; no new competency levels or independence inference."""

from typing import Literal

from pydantic import BaseModel


class ProgressTaskContext(BaseModel):
    """Historical task facts, never a current attainment qualification."""

    task_kind: str
    rubric_version: int | None
    grading_method: str
    reported_hint_count: int
    revised_work: bool
    assistance_coverage: Literal["partial"] = "partial"
    independence: Literal["not_verified"] = "not_verified"


class ProgressReviewedResult(BaseModel):
    label: Literal["Explanation check passed", "Application attempted", "Application check passed"]
    currently_eligible: bool
    exclusion_reason: str | None
    grading_method: str
    review_authority: Literal["learner_review"] = "learner_review"
    independence: Literal["not_verified"] = "not_verified"


class ProgressEvidence(BaseModel):
    reviewed_result: ProgressReviewedResult | None = None
    task_context: ProgressTaskContext | None = None
    id: str
    dimension: str
    recorded_at: str
    score: float
    weight: float
    grader_level: str
    answer_id: str | None = None
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
