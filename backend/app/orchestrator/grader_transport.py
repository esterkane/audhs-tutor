"""Experimental criterion-ID transport; not connected to live grading."""

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from app.schemas.grading import CriterionResult, GradeResult


class CriterionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criterion_id: str
    passed: StrictBool
    evidence: str


class GraderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criterion_results: list[CriterionDecision]
    misconception: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    feedback: str
    next_step: str


@dataclass(frozen=True)
class CriterionSnapshot:
    """Immutable invocation-local mapping, never a persistent assessment identity."""

    criteria: tuple[str, ...]

    def __post_init__(self) -> None:
        # Copy even if a caller supplies a mutable sequence at runtime.
        object.__setattr__(self, "criteria", tuple(self.criteria))
        names = [text.strip().casefold() for text in self.criteria]
        if not names or any(not name for name in names) or len(set(names)) != len(names):
            raise ValueError("Rubric criteria must be nonempty and distinct")

    def rows(self) -> list[dict[str, str]]:
        return [
            {"criterion_id": f"c{i}", "criterion": text} for i, text in enumerate(self.criteria, 1)
        ]

    def resolve(self, response: GraderResponse) -> GradeResult:
        expected = self.rows()
        decisions = {row.criterion_id: row for row in response.criterion_results}
        if (
            len(response.criterion_results) != len(expected)
            or len(decisions) != len(expected)
            or set(decisions) != {row["criterion_id"] for row in expected}
            or any(not row.evidence.strip() for row in response.criterion_results)
        ):
            raise ValueError("Grade does not identify every criterion exactly once")
        return GradeResult(
            criterion_results=[
                CriterionResult(
                    criterion=row["criterion"],
                    passed=decisions[row["criterion_id"]].passed,
                    evidence=decisions[row["criterion_id"]].evidence,
                )
                for row in expected
            ],
            misconception=response.misconception,
            confidence=response.confidence,
            feedback=response.feedback,
            next_step=response.next_step,
        )
