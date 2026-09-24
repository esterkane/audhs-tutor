from typing import Any

from pydantic import BaseModel, Field


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


class AssessmentView(BaseModel):
    id: str
    skill_id: str
    kind: str
    question: str
    options: list[str] | None = None
    criteria: list[str] | None = None
    confidence_required: bool = False


class AttemptRequest(BaseModel):
    session_id: str
    assessment_id: str
    answer: str = Field(max_length=20_000)  # code submissions carry code + check results
    confidence_pre: int | None = Field(default=None, ge=1, le=5)
    latency_ms: int | None = None
    hint_count: int = 0


class AttemptResult(BaseModel):
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
