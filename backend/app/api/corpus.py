"""Corpus endpoints: what is ingested, ingest more (local paths under the configured roots — this
is a localhost owner app), re-tier or forget a document, and an inspectable search."""

import asyncio
from pathlib import Path

from fastapi import APIRouter

from app.api.deps import DB, Repo, SettingsDep
from app.core.errors import AppError
from app.knowledge import corpus_stats
from app.knowledge.ingest.service import forget_document, ingest_path, retier_document
from app.knowledge.reindex import latest_version_ids
from app.knowledge.repository import SearchFilters
from app.orchestrator.context import QUARANTINE_FLAGS
from app.orchestrator.tools import TUTOR_MIN_TRUST
from app.schemas.corpus import (
    CorpusStats,
    DocumentList,
    DocumentOut,
    ForgetOut,
    IngestDocResult,
    IngestOut,
    IngestRequest,
    RetierRequest,
    RetrievalConfigOut,
    SearchHit,
    SearchOut,
    SearchRequest,
    SkippedFile,
)

router = APIRouter(prefix="/corpus", tags=["corpus"])


@router.get(
    "/stats",
    summary="Corpus overview: courses, chunks, flags, index state",
    response_model=CorpusStats,
)
async def stats(db: DB, repo: Repo) -> CorpusStats:
    versions = await latest_version_ids(db)
    n_docs, n_versions, n_chunks, flagged = await corpus_stats.totals(db, versions)
    try:
        live = await repo.count()
    except Exception:  # index unreachable: still report SQLite truth
        live = None
    reranker = getattr(repo, "reranker", None)
    return CorpusStats(
        retrieval=RetrievalConfigOut(
            collection=repo.collection,
            reranker=getattr(reranker, "registry_id", None) if reranker is not None else None,
            max_per_document=int(getattr(repo, "max_per_document", 0)),
        ),
        documents=n_docs,
        versions=n_versions,
        chunks=n_chunks,
        flagged_chunks=flagged,
        courses=await corpus_stats.course_stats(db, versions),
        index=await corpus_stats.index_state(db, repo.collection),
        index_count=live,
    )


@router.get(
    "/documents",
    summary="Documents (latest version each), optionally by course",
    response_model=DocumentList,
)
async def documents(db: DB, course: str | None = None) -> DocumentList:
    return DocumentList(documents=await corpus_stats.list_documents(db, course))


def _resolve_ingest_path(raw: str, roots: list[Path]) -> Path:
    """Resolve and gate a request path: under a configured root, no dot-folders, must exist."""
    path = Path(raw).expanduser().resolve()
    if any(part.startswith(".") for part in path.parts) or not any(
        path == r or r in path.parents for r in roots
    ):
        raise AppError(
            "forbidden",
            f"path must be under INGEST_ROOTS ({', '.join(str(r) for r in roots)}) "
            "and contain no dot-folders",
            http_status=403,
        )
    if not path.exists():
        raise AppError("not_found", f"path not found: {path}", http_status=404)
    return path


@router.post(
    "/ingest",
    summary="Ingest a local file or course folder (idempotent by content hash)",
    response_model=IngestOut,
)
async def ingest(req: IngestRequest, db: DB, repo: Repo, settings: SettingsDep) -> IngestOut:
    path = await asyncio.to_thread(_resolve_ingest_path, req.path, settings.ingest_roots_resolved)
    report = await ingest_path(
        db,
        path,
        course=req.course,
        source_type=req.source_type,
        trust_tier=req.trust_tier,
        repo=repo if req.index else None,
    )
    return IngestOut(
        summary=report.summary(),
        results=[
            IngestDocResult(
                document_id=r.document_id,
                title=r.title,
                course=r.course,
                source_type=r.source_type,
                version=r.version,
                chunks=r.chunks,
                changed=r.changed,
                deduped=r.deduped,
                flagged=r.flagged,
                indexed=r.indexed,
                trust_updated=r.trust_updated,
                reverted=r.reverted,
            )
            for r in report.results
        ],
        skipped=[SkippedFile(path=s.path, reason=s.reason) for s in report.skipped],
    )


@router.patch(
    "/documents/{document_id}",
    summary="Re-decide a document's trust tier (provenance + index payload; no re-ingest)",
    response_model=DocumentOut,
)
async def retier(document_id: str, req: RetierRequest, db: DB, repo: Repo) -> DocumentOut:
    await retier_document(db, document_id, req.trust_tier, repo=repo)
    return next(d for d in await corpus_stats.list_documents(db) if d.id == document_id)


@router.delete(
    "/documents/{document_id}",
    summary="Remove a document (all versions) from SQLite and the index",
    response_model=ForgetOut,
)
async def forget(document_id: str, db: DB, repo: Repo) -> ForgetOut:
    n = await forget_document(db, document_id, repo=repo)
    return ForgetOut(document_id=document_id, chunks_removed=n)


@router.post(
    "/search",
    summary="Inspect hybrid retrieval: fused, dense, sparse and rerank scores",
    response_model=SearchOut,
)
async def search(req: SearchRequest, repo: Repo, settings: SettingsDep) -> SearchOut:
    """With `tutor_view`, the tutor's trust floor applies and hits the tutor would quarantine are
    marked (kept visible, so the owner can see what was withheld)."""
    min_trust = req.min_trust_tier
    if req.tutor_view:
        min_trust = max(TUTOR_MIN_TRUST, min_trust or 0)
    filters = SearchFilters(
        course=req.course,
        section=req.section,
        lecture=req.lecture,
        source_type=req.source_type,
        skill_ids=req.skill_ids,
        min_trust_tier=min_trust,
    )
    res = await repo.search(req.query, filters, k=req.k)
    return SearchOut(
        query=req.query,
        hits=[
            SearchHit(
                chunk_id=h.chunk.id,
                rank=h.rank,
                score=h.score,
                dense_score=h.dense_score,
                sparse_score=h.sparse_score,
                rerank_score=h.rerank_score,
                citation=h.chunk.provenance.citation(),
                course=h.chunk.provenance.course,
                section=h.chunk.provenance.section,
                lecture=h.chunk.provenance.lecture,
                source_type=h.chunk.provenance.source_type,
                trust_tier=h.chunk.provenance.trust_tier,
                t_start=h.chunk.provenance.t_start,
                flagged=h.flagged,
                quarantined=bool(
                    h.chunk.provenance.trust_tier < settings.quarantine_below_trust
                    and QUARANTINE_FLAGS & set(h.flagged)
                ),
                text=h.chunk.text,
            )
            for h in res.hits
        ],
        latency_ms=res.trace.latency_ms,
        reranked=res.trace.reranked is not None,
        flagged_patterns=res.trace.flagged_patterns,
        collection=res.trace.collection,
    )
