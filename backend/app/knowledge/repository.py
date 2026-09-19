"""RetrievalRepository interface (ADR-0002). Results are ScoredChunks with provenance, not strings."""

from typing import Protocol

from pydantic import BaseModel, Field

from app.db.traces import RetrievalTraceRecord
from app.knowledge.provenance import Provenance


class ChunkRecord(BaseModel):
    id: str
    text: str
    provenance: Provenance
    skill_ids: list[str] = Field(default_factory=list)
    document_id: str | None = None
    ordinal: int = 0


class SearchFilters(BaseModel):
    course: str | None = None
    section: str | None = None
    lecture: str | None = None
    source_type: str | None = None
    skill_ids: list[str] | None = None  # any-of
    document_ids: list[str] | None = None
    min_trust_tier: int | None = None

    def is_empty(self) -> bool:
        return not any(v for v in self.model_dump().values())


class ScoredChunk(BaseModel):
    chunk: ChunkRecord
    score: float  # fused
    dense_score: float | None = None
    sparse_score: float | None = None
    rerank_score: float | None = None
    rank: int
    flagged: list[str] = Field(default_factory=list)


class SearchResult(BaseModel):
    hits: list[ScoredChunk]
    trace: RetrievalTraceRecord


class RetrievalRepository(Protocol):
    collection: str

    async def upsert(self, chunks: list[ChunkRecord]) -> int: ...

    async def search(
        self, query: str, filters: SearchFilters | None = None, k: int = 8
    ) -> SearchResult: ...

    async def delete(self, ids: list[str]) -> None: ...

    async def count(self) -> int: ...

    async def reindex(self, chunks: list[ChunkRecord]) -> int: ...


def rrf(rankings: list[list[str]], k: int = 60) -> dict[str, float]:
    """Reciprocal-rank fusion over ordered id lists (used by the SQLite adapter and tests)."""
    fused: dict[str, float] = {}
    for ranking in rankings:
        for rank, cid in enumerate(ranking):
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (k + rank + 1)
    return dict(sorted(fused.items(), key=lambda kv: kv[1], reverse=True))


def matches(chunk: ChunkRecord, f: SearchFilters | None) -> bool:
    if f is None:
        return True
    p = chunk.provenance
    if f.course and p.course != f.course:
        return False
    if f.section and p.section != f.section:
        return False
    if f.lecture and p.lecture != f.lecture:
        return False
    if f.source_type and p.source_type != f.source_type:
        return False
    if f.min_trust_tier is not None and p.trust_tier < f.min_trust_tier:
        return False
    if f.skill_ids and not set(f.skill_ids) & set(chunk.skill_ids):
        return False
    if f.document_ids and chunk.document_id not in f.document_ids:
        return False
    return True
