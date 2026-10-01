"""Answer-bound formative feedback; quote validity is not semantic correctness."""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FeedbackPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learner_quote: str = Field(min_length=1, max_length=400)
    finding: Literal["supported", "needs_revision", "needs_more_information"]
    explanation: str = Field(min_length=1, max_length=600)


class QuotedFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid")

    points: list[FeedbackPoint] = Field(min_length=1, max_length=3)
    next_step: str = Field(min_length=1, max_length=400)
    followup_question: str | None = Field(default=None, max_length=300)


def bound_feedback(answer: str, *, socratic: bool) -> type[QuotedFeedback]:
    """Validate literal attribution and explicit mode only, never assessment correctness.

    The answer stays in the validation closure; it is not embedded in JSON schema or errors.
    Each class has independent request scope, with no global learner state or model routing.
    """
    if not answer.strip() or len(answer) > 8000:
        raise ValueError("A nonempty bounded learner answer is required")

    class BoundFeedback(QuotedFeedback):
        @model_validator(mode="after")
        def exact_attribution(self) -> Self:
            for point in self.points:
                if not point.learner_quote.strip() or point.learner_quote not in answer:
                    raise ValueError(
                        "Each learner_quote must be a verbatim substring of learner_answer"
                    )
            if len({point.learner_quote for point in self.points}) != len(self.points):
                raise ValueError("Do not repeat the same quoted passage")
            if not socratic and self.followup_question is not None:
                raise ValueError("Explicit feedback must not add a followup_question")
            return self

    return BoundFeedback
