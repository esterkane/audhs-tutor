"""Advisory model outcome contract for model-checked free-text explanations.

Deliberately not an AttemptResult: no score, verdict, mastery or review schedule.
The persistence layer supplies IDs and immutable content binding, never the model.
"""

from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field

PROVISIONAL_POLICY: Final = "model-feedback.v1"


class ProvisionalCriterionFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    criterion: str = Field(min_length=1)
    observation: str = Field(min_length=1)


class ProvisionalFeedbackResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    outcome: Literal["provisional_feedback"] = "provisional_feedback"
    policy_version: Literal["model-feedback.v1"] = PROVISIONAL_POLICY
    feedback_id: str = Field(min_length=1)
    assessment_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    skill_id: str = Field(min_length=1)
    content_version: str = Field(min_length=1)
    previous_assessed_attempt_id: str | None = None
    answer_id: str | None = None
    revision_of_feedback_id: str | None = None
    feedback: str = Field(min_length=1)
    next_step: str
    criterion_feedback: list[ProvisionalCriterionFeedback]
    model_route: str = Field(min_length=1)
