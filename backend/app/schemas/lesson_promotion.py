"""Explicit private lesson authoring input; source identity is server-resolved."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.schemas.answer_lesson_binding import AnswerLessonBinding
from app.schemas.common import Domain
from app.schemas.visual_binding import Identifier

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]


class CreateLessonDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    binding: AnswerLessonBinding
    domain: Domain
    prerequisites: tuple[Identifier, ...] = Field(default=(), max_length=20)
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
    objective: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
    ]
    explanation: Text
    worked_example: Text
    question: Text
    criteria: tuple[Text, ...] = Field(min_length=1, max_length=12)

    @field_validator("criteria")
    @classmethod
    def distinct(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len({v.casefold() for v in value}) != len(value):
            raise ValueError("Rubric criteria must be distinct")
        return value


class LessonDraftReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    action: Literal["create_private_draft"] = "create_private_draft"
    draft_id: Identifier
    promotion_id: Identifier
    created_version: Literal[1] = 1
    # Receipt of creation, not the draft's current state after later edits/discard.


class LessonDraftPreview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    binding: AnswerLessonBinding
    grounding: Literal["unknown", "ungrounded", "sources_recorded"]
    issues: tuple[str, ...]
    # Neither a factual accuracy review nor a permission decision.
    publication_available: Literal[False] = False
