"""Read-only access to completed saved responses; not a grading result."""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class AnswerSummary(BaseModel):
    id: str
    turn_id: str
    session_id: str | None
    surface: str
    created_at: str
    request_text: str
    learner_question: str | None = None
    target_label: str | None = None
    preview: str
    skill_id: str | None
    area_id: str | None


class AnswerPage(BaseModel):
    items: list[AnswerSummary]
    next_cursor: str | None = None


class AnswerDetail(AnswerSummary):
    text: str
    request: dict[str, Any]
    metadata: dict[str, Any]


class AnswerFollowup(BaseModel):
    purpose: Literal["followup", "correction"] = "followup"
    session_id: str
    question: str = Field(min_length=1, max_length=2000)

    @field_validator("question")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Enter a follow-up question")
        return value.strip()


class AnswerFeedbackState(BaseModel):
    verdict: Literal["helpful", "confusing", "incorrect", "outdated"] | None = None
    note: str = Field(default="", max_length=2000)
    hidden: bool = False
    revision: int = Field(default=0, ge=0)


class SavedSourceStatus(BaseModel):
    chunk_id: str
    status: Literal["unchanged", "changed", "missing", "unverifiable"]
    newer_version: bool = False


class SavedSourceCheck(BaseModel):
    sources: list[SavedSourceStatus]
    omitted: int = 0


class AnswerReplacementState(BaseModel):
    replacement_id: str | None = Field(default=None, min_length=1, max_length=128)
    revision: int = Field(default=0, ge=0)
