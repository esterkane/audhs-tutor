"""Private authoring drafts; saving never validates or publishes an assessment."""

import json
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID


class CreateCorrectionDraft(Command):
    assessment_id: str = Field(min_length=1, max_length=100)
    feedback_id: str | None = Field(default=None, min_length=1, max_length=100)
    expected_question_revision: int = Field(ge=0, strict=True)
    expected_content_version: str | None = Field(default=None, pattern=r"^ac1\.[0-9a-f]{64}$")


class SaveCorrectionDraft(Command):
    expected_revision: int = Field(ge=1, strict=True)
    candidate: dict[str, JsonValue]
    rationale: str = Field(default="", max_length=4000)

    @model_validator(mode="after")
    def bounded_json(self) -> "SaveCorrectionDraft":
        if len(json.dumps(self.candidate, allow_nan=False).encode()) > 100_000:
            raise ValueError("Candidate exceeds the draft size limit")
        return self


class DiscardCorrectionDraft(Command):
    expected_revision: int = Field(ge=1, strict=True)


class CorrectionDraftReceipt(BaseModel):
    draft_id: str
    revision: int
    status: str


class CreateCorrectionDraftRequest(CreateCorrectionDraft):
    expected_content_version: str = Field(pattern=r"^ac1\.[0-9a-f]{64}$")


class CorrectionSource(BaseModel):
    assessment_id: str
    kind: str
    candidate: dict[str, JsonValue]
    question_revision: int
    content_version: str
    contains_reference_answers: Literal[True] = True


class CorrectionProblem(BaseModel):
    field: str
    message: str


class CorrectionReview(BaseModel):
    problems: list[CorrectionProblem]
    content_changed: bool
    question_state_changed: bool
    source_status: Literal["not_captured", "changed", "incomplete", "unchanged"]
    draft_status: Literal["draft", "discarded"]
    publication_available: Literal[False] = False


class CorrectionDraftSummary(BaseModel):
    id: str
    assessment_id: str
    revision: int
    status: Literal["draft", "discarded"]
    kind: str
    updated_at: str


class CorrectionDraftView(CorrectionDraftSummary):
    candidate: dict[str, JsonValue]
    original_candidate: dict[str, JsonValue]
    rationale: str
    review: CorrectionReview
    contains_reference_answers: Literal[True] = True


class CorrectionDraftList(BaseModel):
    items: list[CorrectionDraftSummary]
    total: int
    offset: int
    limit: int


class CorrectionPassage(BaseModel):
    reference: str
    status: str
    text: str | None = None
    truncated: bool = False
    document_version_id: str | None = None


class CorrectionImpact(BaseModel):
    draft_id: str
    revision: int
    preview_token: str
    affected_reviews: int
    linked_exercises: int
    passages: list[CorrectionPassage]
    review: CorrectionReview
    publication_available: Literal[False] = False
