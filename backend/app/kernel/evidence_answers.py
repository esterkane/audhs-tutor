"""Source-bound answer plans: copy facts and execute host-registered comparisons.

The model chooses IDs, never factual values, operators, source paths or explanatory prose.
The caller owns source authorization, semantic coverage and the permitted fact IDs for each slot.
A valid plan proves its assembly, not that an arbitrary natural-language question was interpreted.
"""

import hashlib
import json
import math
import operator
import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

Kind = Literal["observed_tool_result", "accepted_material", "learner_statement", "tutor_claim"]
Scalar = str | int | float | bool | None
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}\Z")


class UnsupportedPlan(ValueError):
    pass


def _json(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _identifier(value: str) -> None:
    if not IDENTIFIER.fullmatch(value):
        raise UnsupportedPlan("Invalid source, fact or slot identifier")


@dataclass(frozen=True)
class EvidenceSource:
    id: str
    kind: Kind
    canonical_json: str
    revision: str

    @classmethod
    def capture(cls, identity: str, kind: Kind, payload: Any) -> "EvidenceSource":
        _identifier(identity)
        if kind not in {
            "observed_tool_result",
            "accepted_material",
            "learner_statement",
            "tutor_claim",
        }:
            raise UnsupportedPlan("Unknown evidence provenance")
        encoded = _json(payload)
        if len(encoded.encode()) > 1_000_000:
            raise UnsupportedPlan("Source exceeds the per-request evidence bound")
        return cls(identity, kind, encoded, hashlib.sha256(encoded.encode()).hexdigest())


@dataclass(frozen=True)
class ValueBinding:
    id: str
    source_id: str
    pointer: str
    quoted: bool = False


@dataclass(frozen=True)
class PresenceBinding:
    id: str
    source_id: str
    pointer: str


@dataclass(frozen=True)
class Comparison:
    id: str
    left: str
    right: str
    operation: Literal["gt", "ge", "lt", "le", "eq", "ne"]


@dataclass(frozen=True)
class SourceRef:
    source_id: str
    revision: str
    pointer: str
    kind: Kind


@dataclass(frozen=True)
class EvidenceFact:
    id: str
    value: Scalar
    references: tuple[SourceRef, ...]
    quoted: bool = False
    expression: str | None = None


def _lookup(payload: Any, pointer: str) -> Any:
    if len(pointer) > 256 or pointer and not pointer.startswith("/"):
        raise UnsupportedPlan("Invalid JSON pointer")
    if not pointer:
        return payload
    segments = pointer[1:].split("/")
    if len(segments) > 16:
        raise UnsupportedPlan("Source path is too deep")
    value = payload
    for segment in segments:
        if re.search(r"~(?![01])", segment):
            raise UnsupportedPlan("Invalid pointer escape")
        key = segment.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict) and key in value:
            value = value[key]
        elif (
            isinstance(value, list)
            and re.fullmatch(r"0|[1-9][0-9]*", key)
            and int(key) < len(value)
        ):
            value = value[int(key)]
        else:
            raise UnsupportedPlan("The selected source field is absent")
    return value


def _number(value: Scalar) -> bool:
    return type(value) in {int, float} and (not isinstance(value, float) or math.isfinite(value))


@dataclass(frozen=True)
class FactCatalog:
    facts: Mapping[str, EvidenceFact]
    digest: str

    @classmethod
    def build(
        cls,
        sources: list[EvidenceSource],
        bindings: list[ValueBinding | PresenceBinding],
        comparisons: list[Comparison],
    ) -> "FactCatalog":
        if len(sources) > 32 or len(bindings) + len(comparisons) > 128:
            raise UnsupportedPlan("Evidence catalog exceeds its request bound")
        if len({s.id for s in sources}) != len(sources):
            raise UnsupportedPlan("Duplicate source identifier")
        source_map = {s.id: s for s in sources}
        facts: dict[str, EvidenceFact] = {}
        for binding in bindings:
            _identifier(binding.id)
            if binding.id in facts or binding.source_id not in source_map:
                raise UnsupportedPlan("Duplicate fact or missing source")
            source = source_map[binding.source_id]
            if hashlib.sha256(source.canonical_json.encode()).hexdigest() != source.revision:
                raise UnsupportedPlan("Source revision is inconsistent")
            value = _lookup(json.loads(source.canonical_json), binding.pointer)
            if isinstance(binding, PresenceBinding):
                if source.kind in {"learner_statement", "tutor_claim"}:
                    raise UnsupportedPlan(
                        "Unverified statements cannot establish recorded presence"
                    )
                reference = SourceRef(source.id, source.revision, binding.pointer, source.kind)
                present = value is not None
                facts[binding.id] = EvidenceFact(
                    binding.id,
                    present,
                    (reference,),
                    expression=f"{source.id}{binding.pointer} is not null = {_json(present)}",
                )
                continue
            if type(value) not in {str, int, float, bool, type(None)}:
                raise UnsupportedPlan("Select a scalar source field, not an object")
            if isinstance(value, str) and len(value.encode()) > 8000:
                raise UnsupportedPlan("Select a bounded original passage")
            if binding.quoted and not isinstance(value, str):
                raise UnsupportedPlan("Only original text can be quoted")
            if not binding.quoted and source.kind in {"learner_statement", "tutor_claim"}:
                raise UnsupportedPlan("Unverified statements can only be attributed quotes")
            reference = SourceRef(source.id, source.revision, binding.pointer, source.kind)
            facts[binding.id] = EvidenceFact(binding.id, value, (reference,), binding.quoted)
        operations = {
            "gt": operator.gt,
            "ge": operator.ge,
            "lt": operator.lt,
            "le": operator.le,
            "eq": operator.eq,
            "ne": operator.ne,
        }
        symbols = {"gt": ">", "ge": ">=", "lt": "<", "le": "<=", "eq": "==", "ne": "!="}
        for comparison in comparisons:
            _identifier(comparison.id)
            if (
                comparison.id in facts
                or comparison.left not in facts
                or comparison.right not in facts
                or comparison.operation not in operations
            ):
                raise UnsupportedPlan("Comparison is not registered against existing facts")
            left, right = facts[comparison.left], facts[comparison.right]
            if left.quoted or right.quoted or not _number(left.value) or not _number(right.value):
                raise UnsupportedPlan(
                    "Comparisons require finite numeric evidence, not booleans or quotes"
                )
            value = operations[comparison.operation](
                cast(int | float, left.value), cast(int | float, right.value)
            )
            refs = tuple(dict.fromkeys((*left.references, *right.references)))
            expression = f"{_json(left.value)} {symbols[comparison.operation]} {_json(right.value)} = {_json(value)}"
            facts[comparison.id] = EvidenceFact(comparison.id, value, refs, expression=expression)
        frozen = MappingProxyType(facts)
        identity = _json(
            [
                {
                    "id": f.id,
                    "value": f.value,
                    "quoted": f.quoted,
                    "expression": f.expression,
                    "references": [
                        {
                            "source": r.source_id,
                            "revision": r.revision,
                            "pointer": r.pointer,
                            "kind": r.kind,
                        }
                        for r in f.references
                    ],
                }
                for f in facts.values()
            ]
        )
        return cls(frozen, hashlib.sha256(identity.encode()).hexdigest())


class PlanSlot(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    slot: str = Field(min_length=1, max_length=120)
    fact_id: str = Field(min_length=1, max_length=120)


class EvidencePlan(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    catalog_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    slots: list[PlanSlot] = Field(min_length=1, max_length=24)


def assemble(
    plan: EvidencePlan, catalog: FactCatalog, contract: Mapping[str, frozenset[str]]
) -> tuple[tuple[str, EvidenceFact], ...]:
    """Reject stale plans, missing coverage and facts outside a host-authored slot contract."""
    if plan.catalog_digest != catalog.digest:
        raise UnsupportedPlan("The plan refers to a different evidence revision")
    requested = [entry.slot for entry in plan.slots]
    if len(set(requested)) != len(requested) or set(requested) != set(contract):
        raise UnsupportedPlan("The plan does not cover the exact required answer slots")
    chosen = {entry.slot: entry.fact_id for entry in plan.slots}
    result = []
    for slot, allowed in contract.items():
        _identifier(slot)
        fact_id = chosen[slot]
        if fact_id not in allowed or fact_id not in catalog.facts:
            raise UnsupportedPlan("The selected fact is not permitted for this answer slot")
        result.append((slot, catalog.facts[fact_id]))
    return tuple(result)
