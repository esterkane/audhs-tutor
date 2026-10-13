"""Private history projections; review records are historical, never certification."""

from typing import Literal

from pydantic import BaseModel

from app.schemas.answer_visual_binding import AnswerVisualBinding
from app.schemas.authored_visuals import VisualOrigin, VisualSpec


class VisualDocumentSummary(BaseModel):
    id: str
    title: str
    revision: int
    archived: bool
    updated_at: str


class VisualVersionSummary(BaseModel):
    id: str
    version: int
    content_sha256: str
    snapshot_sha256: str
    target_kind: str
    target_id: str
    created_at: str


class VisualReviewRecord(BaseModel):
    id: str
    decision: str
    note: str
    content_sha256: str
    snapshot_sha256: str
    created_at: str


class VisualVersionDetail(VisualVersionSummary):
    spec: VisualSpec | None
    origin: VisualOrigin | None = None
    grounding_now: Literal[
        "sources_recorded",
        "ungrounded",
        "unavailable_or_changed",
        "snapshot_unavailable",
        "source_excluded",
        "invalid_content",
    ]
    review_meaning: Literal["historical_presentation_review_only"] = (
        "historical_presentation_review_only"
    )


class AnswerVisualTarget(BaseModel):
    binding: AnswerVisualBinding
    grounding: Literal["sources_recorded", "ungrounded", "unknown"]
    source_chunk_ids: list[str]
    sources_omitted: int
    issues: list[str]
    meaning: Literal["target_snapshot_not_approval"] = "target_snapshot_not_approval"
