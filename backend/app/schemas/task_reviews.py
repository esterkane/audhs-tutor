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


class TaskReviewPreview(BaseModel):
    assessment_id: str
    content_version: str
    content: dict[str, object]
    current_review: TaskReviewReceipt | None
    approval_matches_content: bool
    reviewable: bool
    unavailable_reason: str | None


class FrozenReviewIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    receipt_id: str = Field(min_length=1)
    assessment_id: str = Field(min_length=1)
    revision: int = Field(ge=1)
    facet: Facet
    policy_version: Literal["task-review-v1"]
    content_fingerprint: str = Field(min_length=1)


class FrozenTaskReview(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal[1] = 1
    review: FrozenReviewIdentity | None
