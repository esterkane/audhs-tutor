"""Read-only report projections; never expose answer keys or whole snapshots."""

from typing import Literal

from pydantic import BaseModel


class CorrectionReport(BaseModel):
    id: str
    target: Literal["assessment", "draft"]
    assessment_id: str | None
    draft_id: str | None
    reported_question: str
    current_question: str | None
    content_status: Literal["unchanged", "changed", "unavailable"]
    labels: list[str]
    note: str
    created_at: str


class CorrectionInbox(BaseModel):
    items: list[CorrectionReport]
    total: int
    offset: int
    limit: int
