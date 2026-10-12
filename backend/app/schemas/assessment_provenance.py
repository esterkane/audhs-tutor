"""Versioned facts captured with a grade, not an attainment classification."""

from typing import Literal

from pydantic import BaseModel, Field


class AssessmentProvenance(BaseModel):
    schema_version: Literal[1] = 1
    task_kind: str
    content_fingerprint: str = Field(min_length=1)
    rubric_version: int | None
    grading_method: str
    # Preserve the accepted request verbatim, including legacy out-of-range reports.
    reported_hint_count: int
    hint_count_origin: Literal["client_report"] = "client_report"
    revision_of_attempt_id: str | None
    assistance_coverage: Literal["partial"] = "partial"
    external_help: Literal["unknown"] = "unknown"
    full_solution_exposure: Literal["not_recorded"] = "not_recorded"
    independence: Literal["not_verified"] = "not_verified"
    qualification: Literal["not_evaluated"] = "not_evaluated"
