"""Request-bound passage selection; only application code reconstructs literal quotes."""

import hashlib
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import PydanticCustomError

from app.schemas.feedback import QuotedFeedback, bound_feedback


def build_passages(answer: str) -> list[dict[str, str | int]]:
    """Preserve exact Unicode spans and every non-whitespace character, in order."""
    if not answer.strip() or len(answer) > 8000:
        raise ValueError("A nonempty bounded learner answer is required")
    digest = hashlib.sha256(answer.encode()).hexdigest()[:16]
    passages: list[dict[str, str | int]] = []
    start = 0
    while start < len(answer):
        while start < len(answer) and answer[start].isspace():
            start += 1
        if start == len(answer):
            break
        end = min(start + 400, len(answer))
        if end < len(answer) and not answer[end].isspace():
            boundary = next((i for i in range(end - 1, start, -1) if answer[i].isspace()), None)
            if boundary is not None:
                end = boundary
        while end > start and answer[end - 1].isspace():
            end -= 1
        passages.append(
            {
                "id": f"p-{digest}-{len(passages)}",
                "text": answer[start:end],
                "start": start,
                "end": end,
            }
        )
        start = end
    return passages


class SelectionPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    passage_id: str = Field(min_length=1, max_length=64)
    finding: Literal["supported", "needs_revision", "needs_more_information"]
    explanation: str = Field(min_length=1, max_length=600)


class FeedbackSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    points: list[SelectionPoint] = Field(min_length=1, max_length=3)
    next_step: str = Field(min_length=1, max_length=400)
    followup_question: str | None = Field(default=None, max_length=300)


def bound_selection(answer: str, *, socratic: bool) -> type[FeedbackSelection]:
    passages = build_passages(answer)
    lookup = {item["id"]: item["text"] for item in passages}

    class BoundSelection(FeedbackSelection):
        points: list[SelectionPoint] = Field(min_length=1, max_length=min(3, len(passages)))

        @model_validator(mode="after")
        def selected_passages(self) -> Self:
            if any(point.passage_id not in lookup for point in self.points):
                raise PydanticCustomError(
                    "selection_unknown", "Select a passage_id from the supplied passages"
                )
            texts = [lookup[point.passage_id] for point in self.points]
            if len(set(texts)) != len(texts):
                raise PydanticCustomError(
                    "quote_duplicate", "Do not repeat the same quoted passage"
                )
            if not socratic and self.followup_question is not None:
                raise PydanticCustomError(
                    "explicit_followup_forbidden",
                    "Explicit feedback must not add a followup_question",
                )
            return self

    return BoundSelection


def to_quoted(answer: str, selection: FeedbackSelection, *, socratic: bool) -> QuotedFeedback:
    checked = bound_selection(answer, socratic=socratic).model_validate(selection.model_dump())
    lookup = {item["id"]: item["text"] for item in build_passages(answer)}
    return bound_feedback(answer, socratic=socratic).model_validate(
        {
            "points": [
                {
                    "learner_quote": lookup[point.passage_id],
                    "finding": point.finding,
                    "explanation": point.explanation,
                }
                for point in checked.points
            ],
            "next_step": checked.next_step,
            "followup_question": checked.followup_question,
        }
    )
