"""Explicit activation intent and immutable receipt; neither is learning evidence."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.answer_visual_binding import Digest
from app.schemas.visual_binding import Identifier


class ActivateLesson(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    promotion_id: Identifier
    expected_version: int = Field(ge=1)
    payload_sha256: Digest


class LessonActivationReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    action: Literal["activate_private_lesson"] = "activate_private_lesson"
    activation_id: Identifier
    promotion_id: Identifier
    draft_id: Identifier
    activated_version: int
    payload_sha256: Digest
    skill_ids: tuple[Identifier, ...]
    object_ids: tuple[Identifier, ...]
    assessment_ids: tuple[Identifier, ...]
    edge_ids: tuple[Identifier, ...]
