from typing import Literal

from pydantic import BaseModel, ConfigDict


class StudyConditions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    noise: Literal["off", "white", "pink", "brown", "other"] = "off"
    presence: Literal["alone", "quiet_companion", "human"] = "alone"
    movement: Literal["none", "brief_movement"] = "none"
    timer: Literal["hidden", "elapsed", "remaining"] = "elapsed"


class ConditionsIn(BaseModel):
    session_id: str
    conditions: StudyConditions


class ConditionsOut(BaseModel):
    id: str
    node_id: str
    conditions: StudyConditions


class ConditionRecall(BaseModel):
    conditions: StudyConditions
    items_reviewed: int
    recalled: int


class ConditionsSummary(BaseModel):
    groups: list[ConditionRecall]
    reading: str = (
        "Self-reported conditions with later review outcomes. These observational counts "
        "do not establish a benefit or identify the best setup. No recommendation is "
        "made without a controlled comparison; same-session performance is excluded."
    )
