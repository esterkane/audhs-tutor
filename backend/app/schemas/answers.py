"""Read-only access to completed saved responses; not a grading result."""

from typing import Any

from pydantic import BaseModel


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
