from typing import Literal

from pydantic import BaseModel, Field


class ReviewRating(BaseModel):
    content_version: str | None = Field(default=None, max_length=100)
    session_id: str
    rating: int = Field(ge=1, le=4)
    confidence_pre: int | None = Field(default=None, ge=1, le=5)
    hint_count: int = Field(default=0, ge=0, le=1000)
    latency_ms: int | None = None


class ReviewOut(BaseModel):
    item_id: str
    due: str
    state: str
    stability: float | None
    predicted_retrievability: float | None


class ReviewRequestState(BaseModel):
    status: Literal["not_found", "unresolved", "completed"]
    result: ReviewOut | None = None
