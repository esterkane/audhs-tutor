"""Constrained citation-placement repair for hosted project replies.

Only source numbers may be inserted. No prose, speech, metadata or history is rewritten.
The output guards check attribution presence, not semantic entailment; the model must
still check that retrieved evidence supports the claim, and may decline the repair.
"""

import re
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, StrictInt


class CitationPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target: int = Field(ge=0, strict=True)
    sources: list[StrictInt] = Field(min_length=1, max_length=20)


class CitationRepair(BaseModel):
    model_config = ConfigDict(extra="forbid")
    patches: list[CitationPatch] = Field(max_length=20)
    unsupported_targets: list[int] = Field(max_length=20)


class RepairDeclined(ValueError):
    """Keep the existing full-repair path; never invent source support."""


@dataclass(frozen=True)
class Target:
    id: int
    end: int
    text: str


@dataclass(frozen=True)
class Placement:
    original: str
    metadata: str
    evidence: tuple[tuple[str, int], ...]
    targets: tuple[Target, ...]
    sources: frozenset[int]


def prepare(turn: Any, context: Any) -> Placement | None:
    from backend.tutor import guard

    if {f.code for f in guard.check(turn, context) if f.severity == "block"} != {"UNCITED_CLAIM"}:
        return None
    if len({citation.n for citation in turn.citations}) != len(turn.citations):
        return None
    sources = frozenset(citation.n for citation in turn.citations)
    if not sources:
        return None
    targets: list[Target] = []
    # Use exact paragraph spans, without normalizing or reconstructing learner text.
    for match in re.finditer(r"\S[\s\S]*?(?=\n[ \t]*\n|\Z)", turn.text):
        paragraph = match.group()
        if not guard.check_uncited_claims(turn.model_copy(update={"text": paragraph}), context):
            continue
        # Complex Markdown retains the existing full repair rather than accidentally
        # extending attribution across a table, code block, heading or list item.
        if "```" in paragraph or re.search(r"(?m)^\s*(?:[|>#]|[-*+]\s|\d+[.)]\s)", paragraph):
            return None
        end = match.end() - (len(paragraph) - len(paragraph.rstrip()))
        targets.append(Target(len(targets), end, paragraph.rstrip()))
    if not 1 <= len(targets) <= 20:
        return None
    return Placement(
        turn.text,
        turn.model_dump_json(exclude={"text", "guard_flags"}),
        tuple(sorted(context.sources.items())),
        tuple(targets),
        sources,
    )


def apply(
    turn: Any, context: Any, placement: Placement, repair: CitationRepair
) -> tuple[str, dict[str, Any]]:
    from backend.tutor import guard

    # Revalidate the complete original against the current evidence context.
    if turn.text != placement.original or prepare(turn, context) != placement:
        raise RepairDeclined("The explanation or source context changed")
    if repair.unsupported_targets:
        raise RepairDeclined("Retrieved sources do not support every target")
    expected = {target.id for target in placement.targets}
    if {patch.target for patch in repair.patches} != expected or len(repair.patches) != len(
        expected
    ):
        raise RepairDeclined("Every target requires exactly one placement")
    patches = {patch.target: patch.sources for patch in repair.patches}
    text = turn.text
    for target in reversed(placement.targets):
        refs = patches[target.id]
        if (
            any(type(ref) is not int for ref in refs)
            or not set(refs) <= placement.sources
            or len(set(refs)) != len(refs)
        ):
            raise RepairDeclined("Use distinct existing source numbers only")
        text = text[: target.end] + " " + "".join(f"[{ref}]" for ref in refs) + text[target.end :]
    repaired = turn.model_copy(update={"text": text})
    if any(f.severity == "block" for f in guard.check(repaired, context)):
        raise RepairDeclined("The repaired answer still fails its output guards")
    return text, turn.model_dump(mode="json", exclude={"text", "guard_flags"})
