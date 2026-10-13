"""Exact Ask target references; separate from lesson objectives and review receipts."""

from typing import Annotated, Literal

from pydantic import Field

from app.schemas.visual_binding import BindingPart, Identifier

Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class AnswerVisualBinding(BindingPart):
    schema_version: Literal["answer-visual-binding.v1"] = "answer-visual-binding.v1"
    answer_id: Identifier
    question_sha256: Digest
    answer_sha256: Digest
    # Covers the original request, date, model/prompt, provenance and all resolved
    # ancestors. Currency is checked separately; this is never an approval receipt.
    lineage_sha256: Digest
    learning_purpose: str | None = Field(default=None, min_length=1, max_length=4000)
