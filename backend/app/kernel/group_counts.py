"""Exact observations conditional on explicitly supplied removal-only group counts.

No dataset inspection, causal inference, fairness verdict or learning evidence writes.
Not yet connected to the public workspace request or model prompt.
"""

from dataclasses import dataclass
from fractions import Fraction
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

Count = Annotated[StrictInt, Field(ge=0, le=1_000_000_000)]


class GroupCount(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str = Field(min_length=1, max_length=80, strict=True)
    before: Count
    after: Count

    @field_validator("label")
    @classmethod
    def trimmed_label(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Group names must not be blank")
        return value

    @model_validator(mode="after")
    def removal_only(self) -> Self:
        if self.after > self.before:
            raise ValueError("After count cannot exceed before count")
        return self


class GroupCountInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    groups: tuple[GroupCount, ...] = Field(min_length=2, max_length=8)

    @model_validator(mode="after")
    def unique_labels(self) -> Self:
        labels = [group.label for group in self.groups]
        if len(set(labels)) != len(labels):
            raise ValueError("Group names must be unique after trimming")
        return self


@dataclass(frozen=True)
class GroupObservation:
    label: str
    before: int
    after: int
    removed: int
    retention: Fraction | None
    representation_before: Fraction | None
    representation_after: Fraction | None


@dataclass(frozen=True)
class GroupComparison:
    before_total: int
    after_total: int
    groups: tuple[GroupObservation, ...]


def _ratio(numerator: int, denominator: int) -> Fraction | None:
    return Fraction(numerator, denominator) if denominator else None


def compare_groups(supplied: GroupCountInput) -> GroupComparison:
    """Ratios describe only the entered groups; zero denominators are undefined.

    The caller must retain the scope: same units and unchanged, nonoverlapping group
    membership, with rows removed rather than added. Counts cannot verify assumptions.
    Labels remain user data, never instructions or verified dataset identities.
    """
    before_total = sum(group.before for group in supplied.groups)
    after_total = sum(group.after for group in supplied.groups)
    return GroupComparison(
        before_total=before_total,
        after_total=after_total,
        groups=tuple(
            GroupObservation(
                label=group.label,
                before=group.before,
                after=group.after,
                removed=group.before - group.after,
                retention=_ratio(group.after, group.before),
                representation_before=_ratio(group.before, before_total),
                representation_after=_ratio(group.after, after_total),
            )
            for group in supplied.groups
        ),
    )
