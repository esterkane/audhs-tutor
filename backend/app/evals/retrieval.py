"""Retrieval evals: recall@k, MRR and citation coverage over a labelled query set (Stage 3).

A label names *where* the answer lives (course + lecture, optionally a phrase the chunk must
contain), not a chunk id — ids change on every re-ingest, lectures do not."""

import time
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from app.knowledge.ingest.normalize import normalize
from app.knowledge.repository import RetrievalRepository, ScoredChunk, SearchFilters


class Expected(BaseModel):
    course: str | None = None
    lecture: str | None = None
    contains: str | None = None

    def matches(self, hit: ScoredChunk) -> bool:
        p = hit.chunk.provenance
        if self.course is not None and normalize(p.course or "") != normalize(self.course):
            return False
        if self.lecture is not None and normalize(p.lecture or "") != normalize(self.lecture):
            return False
        return self.contains is None or normalize(self.contains) in normalize(hit.chunk.text)


class LabelledQuery(BaseModel):
    id: str
    query: str
    expected: list[Expected] = Field(min_length=1)
    filters: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class QueryResult(BaseModel):
    id: str
    query: str
    recall: float
    recall_at_1: float
    recall_at_4: float
    reciprocal_rank: float
    citation_coverage: float
    latency_ms: int
    hits: list[str]  # citations, in rank order
    found: list[bool]  # per expected item


class RetrievalReport(BaseModel):
    k: int
    collection: str
    queries: int
    recall_at_k: float
    recall_at_1: float
    recall_at_4: float
    mrr: float
    citation_coverage: float
    latency_p50_ms: int
    latency_p95_ms: int
    results: list[QueryResult]
    misses: list[str]

    def summary(self) -> dict[str, Any]:
        return self.model_dump(exclude={"results"})


def load_queries(path: Path) -> list[LabelledQuery]:
    raw = yaml.safe_load(path.read_text()) or {}
    return [LabelledQuery.model_validate(q) for q in raw.get("queries", [])]


def has_citation(hit: ScoredChunk) -> bool:
    """A hit is citable when the learner can find it again: course + lecture (or a path) and
    it is not from an untrusted tier."""
    p = hit.chunk.provenance
    return bool((p.course and p.lecture) or p.path) and p.trust_tier >= 1


def recall_at(q: LabelledQuery, hits: list[ScoredChunk], k: int) -> float:
    top = hits[:k]
    return sum(any(e.matches(h) for h in top) for e in q.expected) / len(q.expected)


def score_query(q: LabelledQuery, hits: list[ScoredChunk]) -> tuple[float, float, list[bool]]:
    found = [any(e.matches(h) for h in hits) for e in q.expected]
    recall = sum(found) / len(found)
    rr = 0.0
    for h in hits:
        if any(e.matches(h) for e in q.expected):
            rr = 1.0 / (h.rank + 1)
            break
    return recall, rr, found


def percentile(values: list[int], pct: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * pct)))
    return ordered[idx]


async def evaluate(
    repo: RetrievalRepository, queries: list[LabelledQuery], *, k: int = 8
) -> RetrievalReport:
    results: list[QueryResult] = []
    for q in queries:
        t0 = time.perf_counter()
        res = await repo.search(q.query, SearchFilters.model_validate(q.filters), k=k)
        latency = int((time.perf_counter() - t0) * 1000)
        recall, rr, found = score_query(q, res.hits)
        coverage = sum(has_citation(h) for h in res.hits) / len(res.hits) if res.hits else 0.0
        results.append(
            QueryResult(
                id=q.id,
                query=q.query,
                recall=recall,
                recall_at_1=recall_at(q, res.hits, 1),
                recall_at_4=recall_at(q, res.hits, 4),
                reciprocal_rank=rr,
                citation_coverage=coverage,
                latency_ms=latency,
                hits=[h.chunk.provenance.citation() for h in res.hits],
                found=found,
            )
        )
    n = len(results) or 1
    latencies = [r.latency_ms for r in results]
    return RetrievalReport(
        k=k,
        collection=repo.collection,
        queries=len(results),
        recall_at_k=round(sum(r.recall for r in results) / n, 4),
        recall_at_1=round(sum(r.recall_at_1 for r in results) / n, 4),
        recall_at_4=round(sum(r.recall_at_4 for r in results) / n, 4),
        mrr=round(sum(r.reciprocal_rank for r in results) / n, 4),
        citation_coverage=round(sum(r.citation_coverage for r in results) / n, 4),
        latency_p50_ms=percentile(latencies, 0.5),
        latency_p95_ms=percentile(latencies, 0.95),
        results=results,
        misses=[r.id for r in results if r.recall < 1.0],
    )


def compare(report: RetrievalReport, baseline: dict[str, Any] | None) -> dict[str, float]:
    if not baseline:
        return {}
    keys = ("recall_at_k", "recall_at_4", "recall_at_1", "mrr", "citation_coverage")
    return {
        key: round(float(getattr(report, key)) - float(baseline.get(key, 0.0)), 4) for key in keys
    }
