"""Bounded evidence snapshots for linked coding help; no learning-state writes."""

import hashlib
import json

from pydantic import BaseModel, Field

from app.knowledge.repository import SearchResult
from app.orchestrator.context import (
    DEFAULT_BUDGET,
    QUARANTINE_BELOW_TRUST,
    RetrievedChunk,
    SectionBudget,
    build_packet,
    data_block,
    escape_data,
)

VERSION = "lesson.evidence.v1"


class LessonEvidence(BaseModel):
    version: str = VERSION
    skill_id: str
    title: str
    goal: str
    passages: list[RetrievedChunk] = Field(default_factory=list)
    dropped: list[str] = Field(default_factory=list)
    widened: list[str] = Field(default_factory=list)

    def text_hashes(self) -> dict[str, str]:
        return {p.chunk_id: hashlib.sha256(p.text.encode()).hexdigest() for p in self.passages}

    def identity(self) -> str:
        # Scores are ranking diagnostics, not source content. Preserve passage order because
        # it determines citation numbering. Labels/flags are model-visible and must participate.
        value = {
            "version": self.version,
            "skill_id": self.skill_id,
            "title": self.title,
            "goal": self.goal,
            "passages": [p.model_dump(exclude={"score"}) for p in self.passages],
            "widened": self.widened,
        }
        encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(encoded.encode()).hexdigest()

    def quoted_passages(self) -> str:
        return data_block(
            [
                p.model_copy(
                    update={
                        "citation": escape_data(p.citation),
                        "flagged": [escape_data(flag).replace('"', "'") for flag in p.flagged],
                    }
                )
                for p in self.passages
            ]
        )


def snapshot(
    result: SearchResult,
    *,
    skill_id: str,
    title: str,
    goal: str,
    budget: SectionBudget = DEFAULT_BUDGET,
    quarantine_below_trust: int = QUARANTINE_BELOW_TRUST,
) -> LessonEvidence:
    """Accept server-resolved lesson fields and retain only whole, eligible passages.

    The caller owns retrieval/error handling and trace persistence. This function neither
    certifies corpus freshness nor treats an empty result as a successful grounding claim.
    """
    # Skip blank/duplicate hits before budgeting. Snapshot/model metadata must agree about
    # exactly which text was supplied, even if an adapter accidentally repeats a chunk.
    seen: set[str] = set()
    hits = []
    rejected = []
    for hit in result.hits:
        if not hit.chunk.text.strip() or hit.chunk.id in seen:
            rejected.append("invalid_or_duplicate:" + hit.chunk.id)
            continue
        seen.add(hit.chunk.id)
        hits.append(hit)
    packet = build_packet(
        policy="",
        request="",
        prompt_version=VERSION,
        retrieved=hits,
        budget=budget,
        quarantine_below_trust=quarantine_below_trust,
    )
    widened = result.trace.filters.get("widened", [])
    return LessonEvidence(
        skill_id=skill_id,
        title=title,
        goal=goal,
        passages=packet.retrieved,
        dropped=rejected + packet.dropped,
        widened=[step for step in widened if step in ("course", "corpus")]
        if isinstance(widened, list)
        else [],
    )
