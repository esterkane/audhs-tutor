"""Private answer-to-lesson target identity, never approval or publication permission."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.answer_visual_binding import Digest
from app.schemas.visual_binding import Identifier


class AnswerLessonBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["answer-lesson-binding.v1"] = "answer-lesson-binding.v1"
    answer_id: Identifier
    question_sha256: Digest
    answer_sha256: Digest
    lineage_sha256: Digest
    # Currency is separate from immutable generation lineage and may change independently.
    source_state_sha256: Digest
