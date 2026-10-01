"""hybrid-retrieval slice: optional reranker after fusion, per-document diversity cap, trace fields."""

import httpx
import pytest

from app.knowledge.provenance import Provenance
from app.knowledge.repository import ChunkRecord, ScoredChunk, SearchFilters
from app.knowledge.rerank import cap_per_document, finish_hits, rerank_hits
from app.knowledge.sqlite_hybrid import SqliteHybridRepository
from app.models_ai.fake import FakeProvider
from app.models_ai.provider import ModelSpec

SPEC = ModelSpec(registry_id="fake-embed", provider="fake", model="fake")
DIM = 32


class KeywordReranker:
    """Deterministic stand-in for the cross-encoder: score = query-term overlap."""

    model = "fake-rerank"
    registry_id = "fake-rerank"
    calls: int = 0

    async def score(self, query: str, texts: list[str]) -> list[float]:
        self.calls += 1
        terms = {t.lower() for t in query.split()}
        return [sum(t in text.lower() for t in terms) / (len(terms) or 1) for text in texts]


def _rec(i: str, text: str, doc: str = "d1") -> ChunkRecord:
    return ChunkRecord(
        id=i,
        text=text,
        document_id=doc,
        provenance=Provenance(source_id=doc, path=f"{doc}.md", source_type="markdown", course="C"),
    )


def _hits(*recs: ChunkRecord) -> list[ScoredChunk]:
    return [ScoredChunk(chunk=r, score=1.0 / (i + 1), rank=i) for i, r in enumerate(recs)]


async def test_rerank_reorders_and_keeps_fused_score() -> None:
    hits = _hits(
        _rec("a", "Unrelated text about cooking pasta."),
        _rec("b", "Rotary position embeddings rotate query and key vectors."),
        _rec("c", "Softmax normalises scores."),
    )
    ordered, scores = await rerank_hits(KeywordReranker(), "rotary position embeddings", hits, k=2)
    assert [h.chunk.id for h in ordered] == ["b", "a"] or [h.chunk.id for h in ordered] == [
        "b",
        "c",
    ]
    assert ordered[0].rerank_score == 1.0 and ordered[0].score == 0.5  # fused score preserved
    assert [h.rank for h in ordered] == [0, 1] and set(scores) == {"a", "b", "c"}  # all candidates


def test_cap_per_document_keeps_order_and_limits() -> None:
    hits = _hits(
        _rec("a1", "x", "A"),
        _rec("a2", "x", "A"),
        _rec("b1", "x", "B"),
        _rec("a3", "x", "A"),
        _rec("c1", "x", "C"),
    )
    capped = cap_per_document(hits, max_per_document=2)
    assert [h.chunk.id for h in capped] == ["a1", "a2", "b1", "c1"]
    assert cap_per_document(hits, max_per_document=0) == hits


async def test_finish_hits_without_reranker_truncates_and_renumbers() -> None:
    hits = _hits(_rec("a", "x", "A"), _rec("b", "x", "A"), _rec("c", "x", "B"))
    out, reranked = await finish_hits(hits, "q", k=2, reranker=None, cap=1)
    assert [h.chunk.id for h in out] == ["a", "c"] and [h.rank for h in out] == [0, 1]
    assert reranked is None


async def test_sqlite_adapter_reranks_and_traces() -> None:
    rr = KeywordReranker()
    repo = SqliteHybridRepository(
        FakeProvider(vectors_dim=DIM), SPEC, dims=DIM, reranker=rr, max_per_document=2
    )
    docs = [
        _rec("k1", "The KV cache stores keys and values of earlier tokens.", "kv"),
        _rec("k2", "KV cache memory grows linearly with sequence length.", "kv"),
        _rec("k3", "KV cache eviction policies drop old tokens.", "kv"),
        _rec("p1", "Positional encodings inject order into attention.", "pos"),
        _rec("l1", "LoRA adds low-rank adapters to frozen weights.", "lora"),
    ]
    await repo.upsert(docs)
    res = await repo.search("KV cache tokens", k=3)
    ids = [h.chunk.id for h in res.hits]
    assert len(ids) == 3 and sum(i.startswith("k") for i in ids) <= 2  # cap: at most 2 from `kv`
    assert res.hits[0].chunk.id in {"k1", "k3"}  # the two chunks mentioning "tokens" win
    assert all(h.rerank_score is not None for h in res.hits)
    assert res.trace.reranked and set(res.trace.reranked) >= set(ids)  # candidates incl. drops
    assert res.trace.reranker_id == "fake-rerank" and len(res.trace.fused) >= 3 and rr.calls == 1
    plain = SqliteHybridRepository(
        FakeProvider(vectors_dim=DIM), SPEC, dims=DIM, max_per_document=0
    )
    await plain.upsert(docs)
    res2 = await plain.search("KV cache tokens", SearchFilters(course="C"), k=5)
    assert res2.trace.reranked is None and res2.trace.reranker_id is None
    assert all(h.rerank_score is None for h in res2.hits)


def _qdrant_up(url: str) -> bool:
    try:
        return httpx.get(f"{url}/healthz", timeout=1.0).status_code == 200
    except httpx.HTTPError:
        return False


@pytest.mark.integration
async def test_qdrant_rerank_and_cap() -> None:
    from qdrant_client import AsyncQdrantClient

    from app.core.config import get_settings
    from app.knowledge.qdrant_hybrid import QdrantHybridRepository

    url = get_settings().qdrant_url
    if not _qdrant_up(url):
        pytest.skip("Qdrant not reachable")
    client = AsyncQdrantClient(url=url)
    repo = QdrantHybridRepository(
        client,
        FakeProvider(vectors_dim=DIM),
        SPEC,
        dims=DIM,
        embedding_version=998,
        on_disk=False,
        reranker=KeywordReranker(),
        max_per_document=1,
    )
    try:
        await repo.reindex(
            [
                _rec("k1", "The KV cache stores keys and values of earlier tokens.", "kv"),
                _rec("k2", "KV cache memory grows with sequence length.", "kv"),
                _rec("p1", "Positional encodings inject order into attention tokens.", "pos"),
                _rec("l1", "LoRA adds low-rank adapters.", "lora"),
            ]
        )
        res = await repo.search("KV cache tokens", k=3)
        ids = [h.chunk.id for h in res.hits]
        assert len({h.chunk.document_id for h in res.hits}) == len(ids)  # one per document
        assert ids[0] == "k1" and res.hits[0].rerank_score == 1.0
        assert res.trace.reranked and res.trace.fused and res.trace.latency_ms >= 0
    finally:
        await client.delete_collection(repo.collection)
