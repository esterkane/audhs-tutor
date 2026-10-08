"""Internal draft commands, not a grading-valid payload or public editing API."""

import json
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID


class CreateCorrectionDraft(Command):
    assessment_id: str = Field(min_length=1, max_length=100)
    feedback_id: str | None = Field(default=None, min_length=1, max_length=100)
    expected_question_revision: int = Field(ge=0, strict=True)


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
