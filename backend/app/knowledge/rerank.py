"""Optional local cross-encoder reranking after fusion (ADR-0002). The reranker is a registry
model (runtime `fastembed`, role `rerank`, TaskClass.RERANK) so it is pulled, tracked and routed
like every other model; without a ready entry retrieval simply returns the fused order."""

import asyncio
from pathlib import Path
from typing import Any, Protocol

from app.knowledge.repository import ScoredChunk

# Cross-encoder cost is linear in candidates × characters (M4 Pro, MiniLM-L6: 16 × 1800 chars ≈
# 230 ms, 16 × 800 ≈ 80 ms). Chunks start with `title › heading` and their first paragraph, which
# carries the relevance signal, so scoring is capped at this prefix.
RERANK_MAX_CHARS = 800


class Reranker(Protocol):
    model: str
    registry_id: str

    async def score(self, query: str, texts: list[str]) -> list[float]: ...


class FastembedReranker:
    """fastembed TextCrossEncoder (ONNX, CPU). Lazy-loaded, thread-offloaded."""

    def __init__(
        self, model: str, *, cache_dir: Path | None = None, registry_id: str | None = None
    ) -> None:
        self.model = model
        self.registry_id = registry_id or model
        self.cache_dir = cache_dir
        self._encoder: Any = None

    def _load(self) -> Any:
        if self._encoder is None:
            from fastembed.rerank.cross_encoder import TextCrossEncoder

            kwargs: dict[str, Any] = {"model_name": self.model}
            if self.cache_dir is not None:
                kwargs["cache_dir"] = str(self.cache_dir)
            self._encoder = TextCrossEncoder(**kwargs)
        return self._encoder

    async def score(self, query: str, texts: list[str]) -> list[float]:
        if not texts:
            return []

        def _run() -> list[float]:
            return [float(s) for s in self._load().rerank(query, texts)]

        return await asyncio.to_thread(_run)


async def rerank_hits(
    reranker: Reranker, query: str, hits: list[ScoredChunk], *, k: int
) -> tuple[list[ScoredChunk], dict[str, float]]:
    """Score every candidate, sort by rerank score (stable on ties), keep k, renumber ranks.
    The fused score stays on the hit so the trace shows both."""
    scores = await reranker.score(query, [h.chunk.text[:RERANK_MAX_CHARS] for h in hits])
    for h, s in zip(hits, scores, strict=True):
        h.rerank_score = s
    scored = {h.chunk.id: float(h.rerank_score or 0.0) for h in hits}  # every candidate
    ordered = sorted(hits, key=lambda h: (-(h.rerank_score or 0.0), h.rank))[:k]
    for rank, h in enumerate(ordered):
        h.rank = rank
    return ordered, scored


def cap_per_document(hits: list[ScoredChunk], *, max_per_document: int) -> list[ScoredChunk]:
    """Diversity: at most N chunks of the same document in the result (0 = unlimited)."""
    if max_per_document <= 0:
        return hits
    seen: dict[str | None, int] = {}
    out: list[ScoredChunk] = []
    for h in hits:
        key = h.chunk.document_id or h.chunk.id
        if seen.get(key, 0) >= max_per_document:
            continue
        seen[key] = seen.get(key, 0) + 1
        out.append(h)
    return out


async def finish_hits(
    hits: list[ScoredChunk],
    query: str,
    *,
    k: int,
    reranker: Reranker | None,
    cap: int,
) -> tuple[list[ScoredChunk], dict[str, float] | None]:
    """Post-fusion pipeline shared by every adapter: optional rerank of all candidates → per-document
    cap (so the cap keeps each document's best chunk by cross-encoder score, not by fused rank) → top k."""
    scores: dict[str, float] | None = None
    if reranker is not None and hits:
        hits, scores = await rerank_hits(reranker, query, hits, k=len(hits))
    hits = cap_per_document(hits, max_per_document=cap)[:k]
    for rank, h in enumerate(hits):
        h.rank = rank
    return hits, scores  # scores cover all candidates so drops by the cap are reconstructible


def candidate_count(k: int, *, reranker: Reranker | None, cap: int) -> int:
    """How many fused candidates to fetch before rerank/cap: enough that a lecture-specific query
    whose top hits all come from one document still fills k after the cap."""
    if reranker is not None:
        return max(k * 2, k + cap * 2)  # scoring is the expensive part: keep it to ~2k texts
    if cap > 0:
        return max(k * 4, k + cap * 2)  # capping is free: fetch generously
    return k
