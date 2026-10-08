"""Eligibility is a learner decision, not question quality or competency evidence."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class QuestionTransitionIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    request_id: UUID
    expected_revision: int = Field(ge=0, strict=True)
    action: Literal["suspend", "restore"]
    reason: str = Field(default="", max_length=1500)


class QuestionStateOut(BaseModel):
    assessment_id: str
    state: Literal["active", "suspended", "superseded", "retired"]
    revision: int
    reason: str = ""
