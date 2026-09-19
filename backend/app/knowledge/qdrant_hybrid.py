"""Production RetrievalRepository (ADR-0002): Qdrant with named dense + sparse vectors, server-side
RRF, payload filters, scalar quantization, on-disk vectors. Collection = corpus_v<embedding_version>."""

import asyncio
import time
import uuid
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client import models as qm

from app.db.traces import RetrievalTraceRecord
from app.knowledge.provenance import Provenance, flag_instruction_patterns
from app.knowledge.repository import ChunkRecord, ScoredChunk, SearchFilters, SearchResult
from app.models_ai.provider import EmbeddingProvider, ModelSpec

POINT_NS = uuid.UUID("6f1c7d3e-5b1a-4a4e-9c3e-1f2d3c4b5a69")
DENSE, SPARSE = "dense", "sparse"


def point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(POINT_NS, chunk_id))


class SparseEncoder:
    """fastembed BM25 (IDF applied server-side via Modifier.IDF). Lazy-loaded, thread-offloaded."""

    def __init__(self, model_name: str = "Qdrant/bm25") -> None:
        self.model_name = model_name
        self._model: Any = None

    def _load(self) -> Any:
        if self._model is None:
            from fastembed import SparseTextEmbedding

            self._model = SparseTextEmbedding(model_name=self.model_name)
        return self._model

    async def encode(self, texts: list[str]) -> list[qm.SparseVector]:
        def _run() -> list[qm.SparseVector]:
            m = self._load()
            return [
                qm.SparseVector(indices=e.indices.tolist(), values=e.values.tolist())
                for e in m.embed(texts)
            ]

        return await asyncio.to_thread(_run)

    async def encode_query(self, text: str) -> qm.SparseVector:
        def _run() -> qm.SparseVector:
            m = self._load()
            e = next(iter(m.query_embed(text)))
            return qm.SparseVector(indices=e.indices.tolist(), values=e.values.tolist())

        return await asyncio.to_thread(_run)


class QdrantHybridRepository:
    def __init__(
        self,
        client: AsyncQdrantClient,
        embedder: EmbeddingProvider,
        embed_spec: ModelSpec,
        *,
        dims: int,
        embedding_version: int = 1,
        sparse: SparseEncoder | None = None,
        on_disk: bool = True,
        quantize: bool = True,
        batch_size: int = 64,
    ) -> None:
        self.client = client
        self.embedder = embedder
        self.embed_spec = embed_spec
        self.dims = dims
        self.embedding_version = embedding_version
        self.collection = f"corpus_v{embedding_version}"
        self.sparse = sparse or SparseEncoder()
        self.on_disk = on_disk
        self.quantize = quantize
        self.batch_size = batch_size

    # ------------------------------------------------------------------ schema
    async def ensure_collection(self, *, recreate: bool = False) -> None:
        exists = await self.client.collection_exists(self.collection)
        if exists and recreate:
            await self.client.delete_collection(self.collection)
            exists = False
        if exists:
            return
        await self.client.create_collection(
            collection_name=self.collection,
            vectors_config={
                DENSE: qm.VectorParams(
                    size=self.dims, distance=qm.Distance.COSINE, on_disk=self.on_disk
                )
            },
            sparse_vectors_config={
                SPARSE: qm.SparseVectorParams(
                    index=qm.SparseIndexParams(on_disk=self.on_disk), modifier=qm.Modifier.IDF
                )
            },
            quantization_config=(
                qm.ScalarQuantization(
                    scalar=qm.ScalarQuantizationConfig(type=qm.ScalarType.INT8, always_ram=True)
                )
                if self.quantize
                else None
            ),
        )
        for field, schema in (
            ("course", qm.PayloadSchemaType.KEYWORD),
            ("section", qm.PayloadSchemaType.KEYWORD),
            ("lecture", qm.PayloadSchemaType.KEYWORD),
            ("source_type", qm.PayloadSchemaType.KEYWORD),
            ("skill_ids", qm.PayloadSchemaType.KEYWORD),
            ("document_id", qm.PayloadSchemaType.KEYWORD),
            ("trust_tier", qm.PayloadSchemaType.INTEGER),
        ):
            await self.client.create_payload_index(self.collection, field, schema)

    # ------------------------------------------------------------------ write
    async def upsert(self, chunks: list[ChunkRecord]) -> int:
        await self.ensure_collection()
        n = 0
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i : i + self.batch_size]
            texts = [c.text for c in batch]
            dense, sparse = await asyncio.gather(
                self.embedder.embed(self.embed_spec, texts), self.sparse.encode(texts)
            )
            points = [
                qm.PointStruct(
                    id=point_id(c.id),
                    vector={DENSE: d, SPARSE: s},
                    payload={
                        "chunk_id": c.id,
                        "text": c.text,
                        "skill_ids": c.skill_ids,
                        "document_id": c.document_id,
                        "ordinal": c.ordinal,
                        **c.provenance.model_dump(),
                    },
                )
                for c, d, s in zip(batch, dense, sparse, strict=True)
            ]
            await self.client.upsert(self.collection, points=points, wait=True)
            n += len(points)
        return n

    async def delete(self, ids: list[str]) -> None:
        await self.client.delete(
            self.collection,
            points_selector=qm.PointIdsList(points=[point_id(i) for i in ids]),
            wait=True,
        )

    async def count(self) -> int:
        if not await self.client.collection_exists(self.collection):
            return 0
        return int((await self.client.count(self.collection, exact=True)).count)

    async def reindex(self, chunks: list[ChunkRecord]) -> int:
        await self.ensure_collection(recreate=True)
        return await self.upsert(chunks)

    # ------------------------------------------------------------------ read
    @staticmethod
    def _filter(f: SearchFilters | None) -> qm.Filter | None:
        if f is None or f.is_empty():
            return None
        must: list[qm.Condition] = []
        for key in ("course", "section", "lecture", "source_type"):
            val = getattr(f, key)
            if val:
                must.append(qm.FieldCondition(key=key, match=qm.MatchValue(value=val)))
        if f.skill_ids:
            must.append(qm.FieldCondition(key="skill_ids", match=qm.MatchAny(any=f.skill_ids)))
        if f.document_ids:
            must.append(qm.FieldCondition(key="document_id", match=qm.MatchAny(any=f.document_ids)))
        if f.min_trust_tier is not None:
            must.append(qm.FieldCondition(key="trust_tier", range=qm.Range(gte=f.min_trust_tier)))
        return qm.Filter(must=must)

    async def search(
        self, query: str, filters: SearchFilters | None = None, k: int = 8
    ) -> SearchResult:
        t0 = time.perf_counter()
        (dense_q,), sparse_q = await asyncio.gather(
            self.embedder.embed(self.embed_spec, [query]), self.sparse.encode_query(query)
        )
        qfilter = self._filter(filters)
        pre = k * 3
        fused_req = qm.QueryRequest(
            prefetch=[
                qm.Prefetch(query=dense_q, using=DENSE, limit=pre, filter=qfilter),
                qm.Prefetch(query=sparse_q, using=SPARSE, limit=pre, filter=qfilter),
            ],
            query=qm.FusionQuery(fusion=qm.Fusion.RRF),
            limit=k,
            with_payload=True,
        )
        dense_req = qm.QueryRequest(
            query=dense_q, using=DENSE, limit=pre, filter=qfilter, with_payload=False
        )
        sparse_req = qm.QueryRequest(
            query=sparse_q, using=SPARSE, limit=pre, filter=qfilter, with_payload=False
        )
        fused_res, dense_res, sparse_res = await self.client.query_batch_points(
            self.collection, requests=[fused_req, dense_req, sparse_req]
        )
        id_of = {}
        hits: list[ScoredChunk] = []
        fused_scores: dict[str, float] = {}
        for rank, p in enumerate(fused_res.points):
            payload = dict(p.payload or {})
            cid = str(payload.pop("chunk_id"))
            id_of[str(p.id)] = cid
            text = str(payload.pop("text"))
            prov = Provenance.model_validate(
                {k_: payload.get(k_) for k_ in Provenance.model_fields}
            )
            chunk = ChunkRecord(
                id=cid,
                text=text,
                provenance=prov,
                skill_ids=list(payload.get("skill_ids") or []),
                document_id=payload.get("document_id"),
                ordinal=int(payload.get("ordinal") or 0),
            )
            fused_scores[cid] = float(p.score)
            hits.append(
                ScoredChunk(
                    chunk=chunk,
                    score=float(p.score),
                    rank=rank,
                    flagged=flag_instruction_patterns(text),
                )
            )
        dense_scores = {str(p.id): float(p.score) for p in dense_res.points}
        sparse_scores = {str(p.id): float(p.score) for p in sparse_res.points}
        for h in hits:
            pid = point_id(h.chunk.id)
            h.dense_score = dense_scores.get(pid)
            h.sparse_score = sparse_scores.get(pid)
        flagged = sorted({f for h in hits for f in h.flagged})
        trace = RetrievalTraceRecord(
            collection=self.collection,
            query=query,
            filters=filters.model_dump(exclude_none=True) if filters else {},
            bm25_scores={id_of.get(pid, pid): s for pid, s in sparse_scores.items()},
            vector_scores={id_of.get(pid, pid): s for pid, s in dense_scores.items()},
            fused=fused_scores,
            chunk_ids=[h.chunk.id for h in hits],
            flagged_patterns=flagged,
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )
        return SearchResult(hits=hits, trace=trace)
