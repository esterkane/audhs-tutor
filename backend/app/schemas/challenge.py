from typing import Literal

from pydantic import BaseModel, Field

ChallengeMode = Literal["planted_error", "steelman", "teach_back", "calibration"]
CHALLENGE_MODES: list[str] = ["planted_error", "steelman", "teach_back", "calibration"]


class ChallengeItem(BaseModel):
    """Structured output of the challenge generator (Instructor)."""

    prompt: str = Field(min_length=20)
    hidden_key: str = Field(min_length=5)
    criteria: list[str] = Field(min_length=2, max_length=5)


class ChallengeStart(BaseModel):
    session_id: str
    mode: ChallengeMode
    skill_id: str | None = None


class ChallengeView(BaseModel):
    assessment_id: str
    skill_id: str
    mode: ChallengeMode
    prompt: str
    criteria: list[str]
    cached: bool
    sources: list[str]
