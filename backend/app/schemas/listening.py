"""P7 guided listening: lessons from ingested timed documents, bounded clips, one task per clip."""

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.grading import AssessmentView


class LessonSummary(BaseModel):
    document_id: str
    title: str
    course: str | None
    section: str | None
    lecture: str | None
    language: str | None
    sections: int
    done: int
    next_index: int | None = None
    media_available: bool
    duration_s: float | None
    timed_chunks: int


class LessonList(BaseModel):
    lessons: list[LessonSummary]


class SectionOut(BaseModel):
    index: int
    chunk_id: str
    t_start: float
    t_end: float
    text: str
    done: bool
    attempts: int


class SkippedOut(BaseModel):
    chunk_id: str
    reason: str


class LessonOut(BaseModel):
    document_id: str
    title: str
    course: str | None
    lecture: str | None
    language: str | None
    media_url: str | None  # guarded app endpoint, or None → text-only fallback
    media_note: str | None
    duration_s: float | None
    sections: list[SectionOut]
    skipped: list[SkippedOut]
    next_index: int | None


class TaskIn(BaseModel):
    session_id: str
    use_model: bool = Field(
        default=True,
        description="ask the routed local model for a comprehension question; deterministic cloze "
        "when no route is ready or the reply fails the checks",
    )


class TaskOut(BaseModel):
    item: AssessmentView
    origin: str  # model | deterministic
    validated: bool
    problems: list[str]
    citation: str | None
    clip: dict[str, Any]


class ListenedIn(BaseModel):
    session_id: str
    chunk_id: str | None = None  # stable object id (clip indexes shift when cues are skipped)
    replays: int = Field(default=0, ge=0, le=50)
    seconds: float = Field(default=0.0, ge=0.0, le=3600.0)


class ValidateIn(BaseModel):
    validated: bool = True
