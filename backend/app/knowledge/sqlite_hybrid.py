"""Test/offline RetrievalRepository: FTS5 (BM25) + sqlite-vec (falls back to numpy cosine) + RRF."""

import json
import re
import sqlite3
import time
from typing import Any

import numpy as np

from app.db.traces import RetrievalTraceRecord
from app.knowledge.provenance import flag_instruction_patterns
from app.knowledge.repository import (
    ChunkRecord,
    ScoredChunk,
    SearchFilters,
    SearchResult,
    matches,
    rrf,
)
from app.knowledge.rerank import Reranker, candidate_count, finish_hits
from app.models_ai.provider import EmbeddingProvider, ModelSpec


def _fts_query(q: str) -> str:
    toks = [t for t in re.findall(r"[A-Za-z0-9_.\-]+", q) if len(t) > 1]
    return " OR ".join(f'"{t}"' for t in toks) or '""'


class SqliteHybridRepository:
    def __init__(
        self,
        embedder: EmbeddingProvider,
        embed_spec: ModelSpec,
        *,
        dims: int,
        path: str = ":memory:",
        embedding_version: int = 1,
        reranker: Reranker | None = None,
        max_per_document: int = 3,
    ) -> None:
        self.embedder = embedder
        self.embed_spec = embed_spec
        self.dims = dims
        self.collection = f"sqlite_corpus_v{embedding_version}"
        self.reranker = reranker
        self.max_per_document = max_per_document
        self.conn = sqlite3.connect(path)
        self.vec_ext = self._try_load_vec()
        self._schema()

    def _try_load_vec(self) -> bool:
        try:
            import sqlite_vec

            self.conn.enable_load_extension(True)
            sqlite_vec.load(self.conn)
            self.conn.enable_load_extension(False)
            return True
        except Exception:
            return False

    def _schema(self) -> None:
        c = self.conn
        c.execute(
            "CREATE TABLE IF NOT EXISTS chunks (id TEXT PRIMARY KEY, record TEXT NOT NULL, vec TEXT NOT NULL)"
        )
        c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(id UNINDEXED, text)")
        if self.vec_ext:
            ddl = "CREATE VIRTUAL TABLE IF NOT EXISTS chunks_vec USING vec0"
            c.execute(f"{ddl}(id TEXT PRIMARY KEY, embedding float[{self.dims}])")
        c.commit()

    async def upsert(self, chunks: list[ChunkRecord]) -> int:
        vectors = await self.embedder.embed(self.embed_spec, [c.text for c in chunks])
        cur = self.conn.cursor()
        for ch, v in zip(chunks, vectors, strict=True):
            cur.execute("DELETE FROM chunks WHERE id=?", (ch.id,))
            cur.execute("DELETE FROM chunks_fts WHERE id=?", (ch.id,))
            cur.execute(
                "INSERT INTO chunks VALUES (?,?,?)", (ch.id, ch.model_dump_json(), json.dumps(v))
            )
            cur.execute("INSERT INTO chunks_fts VALUES (?,?)", (ch.id, ch.text))
            if self.vec_ext:
                cur.execute("DELETE FROM chunks_vec WHERE id=?", (ch.id,))
                cur.execute("INSERT INTO chunks_vec VALUES (?,?)", (ch.id, json.dumps(v)))
        self.conn.commit()
        return len(chunks)

    async def delete(self, ids: list[str]) -> None:
        for i in ids:
            self.conn.execute("DELETE FROM chunks WHERE id=?", (i,))
            self.conn.execute("DELETE FROM chunks_fts WHERE id=?", (i,))
            if self.vec_ext:
                self.conn.execute("DELETE FROM chunks_vec WHERE id=?", (i,))
        self.conn.commit()

    async def count(self) -> int:
        return int(self.conn.execute("SELECT count(*) FROM chunks").fetchone()[0])

    async def update_payload(self, ids: list[str], payload: dict[str, Any]) -> None:
        for cid in ids:
            row = self.conn.execute("SELECT record FROM chunks WHERE id=?", (cid,)).fetchone()
            if row is None:
                continue
            rec = ChunkRecord.model_validate_json(row[0])
            rec.provenance = rec.provenance.model_copy(update=payload)
            self.conn.execute("UPDATE chunks SET record=? WHERE id=?", (rec.model_dump_json(), cid))
        self.conn.commit()

    async def reindex(self, chunks: list[ChunkRecord]) -> int:
        self.conn.execute("DELETE FROM chunks")
        self.conn.execute("DELETE FROM chunks_fts")
        if self.vec_ext:
            self.conn.execute("DELETE FROM chunks_vec")
        self.conn.commit()
        return await self.upsert(chunks)

    def _load(self, cid: str) -> ChunkRecord:
        row = self.conn.execute("SELECT record FROM chunks WHERE id=?", (cid,)).fetchone()
        return ChunkRecord.model_validate_json(row[0])

    def _bm25(self, query: str, limit: int) -> dict[str, float]:
        rows = self.conn.execute(
            "SELECT id, bm25(chunks_fts) FROM chunks_fts WHERE chunks_fts MATCH ? "
            "ORDER BY bm25(chunks_fts) LIMIT ?",
            (_fts_query(query), limit),
        ).fetchall()
        return {r[0]: -float(r[1]) for r in rows}  # bm25() is negative-better in FTS5

    def _dense(self, qvec: list[float], limit: int) -> dict[str, float]:
        if self.vec_ext:
            rows = self.conn.execute(
                "SELECT id, distance FROM chunks_vec WHERE embedding MATCH ? "
                "ORDER BY distance LIMIT ?",
                (json.dumps(qvec), limit),
            ).fetchall()
            return {r[0]: 1.0 - float(r[1]) for r in rows}
        rows = self.conn.execute("SELECT id, vec FROM chunks").fetchall()
        if not rows:
            return {}
        mat = np.array([json.loads(r[1]) for r in rows], dtype=float)
        q = np.array(qvec, dtype=float)
        sims = mat @ q / (np.linalg.norm(mat, axis=1) * (np.linalg.norm(q) or 1.0) + 1e-9)
        order = np.argsort(-sims)[:limit]
        return {rows[i][0]: float(sims[i]) for i in order}

    async def search(
        self, query: str, filters: SearchFilters | None = None, k: int = 8
    ) -> SearchResult:
        t0 = time.perf_counter()
        (qvec,) = await self.embedder.embed(self.embed_spec, [query])
        pre = max(k * 5, 50)
        bm25 = self._bm25(query, pre)
        dense = self._dense(qvec, pre)
        records: dict[str, ChunkRecord] = {cid: self._load(cid) for cid in set(bm25) | set(dense)}
        keep = {cid for cid, rec in records.items() if matches(rec, filters)}
        bm25 = {c: s for c, s in bm25.items() if c in keep}
        dense = {c: s for c, s in dense.items() if c in keep}
        fused = rrf([list(bm25), list(dense)])
        candidates = candidate_count(k, reranker=self.reranker, cap=self.max_per_document)
        hits = []
        for rank, (cid, score) in enumerate(list(fused.items())[:candidates]):
            rec = records[cid]
            hits.append(
                ScoredChunk(
                    chunk=rec,
                    score=score,
                    rank=rank,
                    dense_score=dense.get(cid),
                    sparse_score=bm25.get(cid),
                    flagged=flag_instruction_patterns(rec.text),
                )
            )
        hits, reranked = await finish_hits(
            hits, query, k=k, reranker=self.reranker, cap=self.max_per_document
        )
        trace = RetrievalTraceRecord(
            collection=self.collection,
            query=query,
            filters=filters.model_dump(exclude_none=True) if filters else {},
            bm25_scores=bm25,
            vector_scores=dense,
            fused=dict(list(fused.items())[:candidates]),
            reranked=reranked,
            reranker_id=self.reranker.registry_id
            if reranked is not None and self.reranker
            else None,
            chunk_ids=[h.chunk.id for h in hits],
            flagged_patterns=sorted({f for h in hits for f in h.flagged}),
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )
        return SearchResult(hits=hits, trace=trace)
