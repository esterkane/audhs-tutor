"""Unverified context suggestions; no learner-state or permission assertions."""

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

Identifier = Annotated[str, StringConstraints(min_length=1, max_length=128, pattern=r"\S")]
Digest = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
FieldName = Literal["task", "notes", "examples", "unresolved"]
LIMITS = {"task": 500, "notes": 1500, "examples": 1000, "unresolved": 500}


class ProposalReference(BaseModel):
    """Offsets count Python Unicode code points, not UTF-16 units or escaped text."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    input_id: Identifier
    text_hash: Digest
    start: int = Field(ge=0, le=24000)
    end: int = Field(ge=1, le=24000)

    @model_validator(mode="after")
    def ordered(self) -> "ProposalReference":
        if self.end <= self.start:
            raise ValueError("Reference must contain a nonempty range")
        return self


class ProposedField(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    field: FieldName
    value: str = Field(max_length=1500)
    rationale: str = Field(min_length=1, max_length=500)
    references: list[ProposalReference] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def bounded(self) -> "ProposedField":
        if len(self.value) > LIMITS[self.field] or not self.rationale.strip():
            raise ValueError("Field limit exceeded or rationale empty")
        if len(set(self.references)) != len(self.references):
            raise ValueError("Duplicate supporting reference")
        return self


class ContextProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    version: Literal[1] = 1
    changes: list[ProposedField] = Field(max_length=4)

    @field_validator("version", mode="before")
    @classmethod
    def exact_version_type(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("Version must be an integer")
        return value

    @model_validator(mode="after")
    def distinct_fields(self) -> "ContextProposal":
        if len({change.field for change in self.changes}) != len(self.changes):
            raise ValueError("Propose each field at most once")
        return self
