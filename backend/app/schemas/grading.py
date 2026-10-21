from typing import Any

from pydantic import BaseModel, Field, model_validator


class CriterionResult(BaseModel):
    criterion: str
    passed: bool
    evidence: str = ""


class GradeResult(BaseModel):
    """Structured grader output (ADR-0009). Never a bare score."""

    criterion_results: list[CriterionResult]
    misconception: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    feedback: str
    next_step: str

    @property
    def score(self) -> float:
        if not self.criterion_results:
            return 0.0
        return sum(1 for c in self.criterion_results if c.passed) / len(self.criterion_results)


def rubric_grade_model(criteria: list[str]) -> type[GradeResult]:
    """Validate rubric identity inside provider parsing so logged repairs can run.

    Never infer identities from list position or accept paraphrased criteria as evidence.
    """
    expected = {name.strip().casefold() for name in criteria}

    class RubricGradeResult(GradeResult):
        @model_validator(mode="after")
        def complete_rubric(self) -> "RubricGradeResult":
            returned = [row.criterion.strip().casefold() for row in self.criterion_results]
            if (
                not expected
                or len(expected) != len(criteria)
                or len(returned) != len(criteria)
                or set(returned) != expected
            ):
                raise ValueError(
                    "Return every rubric criterion exactly once, copying its entire text "
                    "verbatim (including text after a colon): " + repr(criteria)
                )
            if any(not row.evidence.strip() for row in self.criterion_results):
                raise ValueError("Every criterion requires quoted learner evidence or 'absent'.")
            return self

    return RubricGradeResult


class AssessmentView(BaseModel):
    content_version: str | None = None
    id: str
    skill_id: str
    kind: str
    question: str
    options: list[str] | None = None
    criteria: list[str] | None = None
    confidence_required: bool = False


class AttemptRequest(BaseModel):
    revision_of_feedback_id: str | None = Field(default=None, min_length=1, max_length=100)
    revision_of_attempt_id: str | None = Field(default=None, min_length=1, max_length=100)
    content_version: str | None = Field(default=None, max_length=100)
    session_id: str
    assessment_id: str
    answer: str = Field(max_length=20_000)  # code submissions carry code + check results
    confidence_pre: int | None = Field(default=None, ge=1, le=5)
    latency_ms: int | None = None
    hint_count: int = 0

    @model_validator(mode="after")
    def one_revision_parent(self) -> "AttemptRequest":
        if self.revision_of_attempt_id and self.revision_of_feedback_id:
            raise ValueError("Choose one revision parent")
        return self

    def identity_payload(self) -> dict[str, Any]:
        """Preserve historical fingerprints while adding explicit advisory lineage."""
        payload = self.model_dump(mode="json")
        for key in ("revision_of_attempt_id", "revision_of_feedback_id", "content_version"):
            if payload[key] is None:
                payload.pop(key)
        return payload


class AttemptResult(BaseModel):
    revision_of_attempt_id: str | None = None
    review_updated: bool = True
    answer_id: str | None = None
    save_error: str | None = None
    save_receipt: str | None = None
    attempt_id: str
    assessment_id: str
    skill_id: str
    kind: str
    dimension: str
    correct: bool | None
    score: float
    criterion_results: list[CriterionResult]
    misconception: str | None
    confidence: float
    grader_level: str
    feedback: str
    next_step: str
    confidence_pre: int | None
    calibration: str
    review: dict[str, Any]
    mastery: float


# Historical assessed outcomes keep their original shape. Advisory outcomes never
# fabricate the score/review/mastery fields required by AttemptResult.
from app.schemas.provisional_feedback import ProvisionalFeedbackResult  # noqa: E402

AssessmentOutcome = AttemptResult | ProvisionalFeedbackResult
