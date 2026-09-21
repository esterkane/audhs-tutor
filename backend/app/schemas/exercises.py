"""P8 code exercise: source-linked exercise run in the browser (Pyodide), graded from check results."""

from typing import Any

from pydantic import BaseModel, Field


class CheckOut(BaseModel):
    name: str
    criterion: str
    code: str  # run in the browser sandbox after the learner's code; must not raise


class SourceOut(BaseModel):
    chunk_id: str
    citation: str


class ExerciseView(BaseModel):
    assessment_id: str
    skill_id: str
    exercise_id: str
    title: str
    prompt: str
    starter_code: str
    success_criteria: list[str]
    checks: list[CheckOut]
    packages: list[str]
    timeout_s: int
    max_output_chars: int
    sources: list[SourceOut]
    runtime: str
    hints_available: int
    attempts: int
    check_assessment_id: str | None = None  # the check question as an explain-back item
    check_question: str
    policy: dict[str, Any]  # what the runtime may and may not do — shown to the learner


class HintIn(BaseModel):
    session_id: str
    level: int = Field(ge=1, le=10)


class HintOut(BaseModel):
    level: int
    text: str
    hints_available: int


class SolutionIn(BaseModel):
    session_id: str


class SolutionOut(BaseModel):
    solution: str
    check_question: str
