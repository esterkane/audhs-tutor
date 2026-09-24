"""Area organization and explicit question feedback contracts."""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class AreaEdit(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    terms: list[str] = Field(min_length=1, max_length=30)
    description: str = Field(default="", max_length=1000)


class AreaOut(AreaEdit):
    id: str
    slug: str
    documents: int
    courses: list[str]
    draft_ids: list[str]
    related: list[str]


class AreaList(BaseModel):
    areas: list[AreaOut]
    unassigned_documents: int
    total_documents: int


class AreaSources(BaseModel):
    sources: list[dict[str, Any]]


class DraftBatchOut(BaseModel):
    created: list[str]
    existing: list[str]
    skipped: list[dict[str, str]]


class FeedbackIn(BaseModel):
    draft_id: str | None = None
    draft_version: int | None = Field(default=None, ge=1)
    question_index: int | None = Field(default=None, ge=0)
    assessment_id: str | None = None
    verdict: Literal["good", "bad"]
    labels: list[
        Literal[
            "clear",
            "useful_application",
            "connects_ideas",
            "incorrect",
            "off_topic",
            "too_vague",
            "too_easy",
            "too_hard",
            "other",
        ]
    ] = Field(min_length=1, max_length=5)
    note: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def target(self) -> "FeedbackIn":
        if bool(self.draft_id) == bool(self.assessment_id):
            raise ValueError("choose one draft question or active assessment")
        if self.draft_id and (self.draft_version is None or self.question_index is None):
            raise ValueError("draft version and question index are required")
        return self


class FeedbackOut(BaseModel):
    id: str
    target_key: str
    verdict: str
    labels: list[str]
    note: str
    created_at: str
    withdrawn: bool


class FeedbackSuggestion(BaseModel):
    key: str
    description: str
    reason: str


class FeedbackList(BaseModel):
    feedback: list[FeedbackOut]
    label_counts: dict[str, int]
    suggestions: list[FeedbackSuggestion]
    preferences: dict[str, bool]


class FeedbackPreference(BaseModel):
    key: Literal["questions.applied", "questions.connections", "questions.step_by_step"]
    enabled: bool
