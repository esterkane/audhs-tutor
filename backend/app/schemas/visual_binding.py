"""Strict references for a visual attached to one exact learning-object version."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Identifier = Annotated[str, Field(min_length=1, max_length=128)]


class BindingPart(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class CriterionRef(BindingPart):
    index: int = Field(ge=0, le=255)
    text: str = Field(min_length=1, max_length=4000)


class VisualSourceRef(BindingPart):
    chunk_id: Identifier
    document_version_id: Identifier
    text_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class VisualBinding(BindingPart):
    schema_version: Literal["visual-binding.v1"]
    object_id: Identifier
    object_version: int = Field(ge=1)
    skill_id: Identifier
    goal: str = Field(min_length=1, max_length=4000)
    criteria: tuple[CriterionRef, ...] = Field(min_length=1, max_length=32)
    sources: tuple[VisualSourceRef, ...] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def unique_references(self) -> "VisualBinding":
        if len({ref.index for ref in self.criteria}) != len(self.criteria):
            raise ValueError("duplicate criterion index")
        if len({ref.chunk_id for ref in self.sources}) != len(self.sources):
            raise ValueError("duplicate source chunk")
        return self
