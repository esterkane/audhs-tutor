"""Explicit task/rubric review, separate from assessed learner performance."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Facet = Literal["explanation", "application"]
Decision = Literal["approve", "revoke"]


class TaskReviewCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    expected_revision: int = Field(ge=0, strict=True)
    content_version: str = Field(min_length=1, max_length=200)
    decision: Decision
    facet: Facet
    confirmed: bool = Field(strict=True)


class TaskReviewReceipt(BaseModel):
    id: str
    assessment_id: str
    revision: int
    decision: Decision
    facet: Facet
    policy_version: str
    reviewed_at: str
