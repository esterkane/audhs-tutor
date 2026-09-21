"""Observability writers: tutor_trace, retrieval_trace, model_call. No trace = bug."""

from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ModelCall, RetrievalTrace, TutorTrace
from app.models_ai.provider import HOSTED_PROVIDERS


class ModelCallRecord(BaseModel):
    provider: str
    model: str
    registry_id: str
    task: str
    route: str = "primary"
    tokens_in: int = 0
    tokens_out: int = 0
    cached_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    cached: bool = False
    ok: bool = True
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    learner_id: str | None = None
    session_id: str | None = None
    # P6 accounting
    request_id: str | None = None
    attempt: int = 1
    idempotency_key: str | None = None
    outcome: str = "ok"  # ok | error | invalid_output | cancelled | partial | blocked
    usage_source: str = "unavailable"  # reported | estimated | unavailable | legacy
    cost_status: str = "free"  # free | reported | estimated | unknown | legacy
    reserved_usd: float = 0.0


class RetrievalTraceRecord(BaseModel):
    collection: str
    query: str
    filters: dict[str, Any] = Field(default_factory=dict)
    bm25_scores: dict[str, float] = Field(default_factory=dict)
    vector_scores: dict[str, float] = Field(default_factory=dict)
    fused: dict[str, float] = Field(default_factory=dict)
    reranked: dict[str, float] | None = None
    reranker_id: str | None = None
    chunk_ids: list[str] = Field(default_factory=list)
    flagged_patterns: list[str] = Field(default_factory=list)
    latency_ms: int = 0
    learner_id: str | None = None
    session_id: str | None = None


class TutorTraceRecord(BaseModel):
    learner_id: str
    session_id: str
    turn_id: str
    action: str
    prompt_version: str
    sections: dict[str, int] = Field(default_factory=dict)
    dropped: list[str] = Field(default_factory=list)
    model_call_id: str | None = None
    retrieval_trace_id: str | None = None
    latency_ms: int = 0


async def write_model_call(
    db: AsyncSession, rec: ModelCallRecord, *, commit: bool = True
) -> ModelCall:
    """One row per provider attempt. An `idempotency_key` already present returns the existing
    row instead of a second one (a retried write never double-counts)."""
    if rec.idempotency_key:
        existing = (
            await db.execute(
                select(ModelCall).where(ModelCall.idempotency_key == rec.idempotency_key)
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing
    cost_status = rec.cost_status
    if rec.request_id is None and cost_status == "free" and rec.provider in HOSTED_PROVIDERS:
        # a hosted row written outside the gateway without an explicit status: priced by tokens →
        # estimated; claiming zero cost is never "free" by default — its billing is unknown
        cost_status = "estimated" if rec.cost_usd > 0 else "unknown"
    row = ModelCall(
        learner_id=rec.learner_id,
        session_id=rec.session_id,
        provider=rec.provider,
        model=rec.model,
        registry_id=rec.registry_id,
        task=rec.task,
        route=rec.route,
        tokens_in=rec.tokens_in,
        tokens_out=rec.tokens_out,
        cached_tokens=rec.cached_tokens,
        cost_usd=rec.cost_usd,
        latency_ms=rec.latency_ms,
        cached=rec.cached,
        ok=rec.ok,
        error=rec.error,
        metadata_json=rec.metadata,
        request_id=rec.request_id,
        attempt=rec.attempt,
        idempotency_key=rec.idempotency_key,
        outcome=rec.outcome,
        usage_source=rec.usage_source,
        cost_status=cost_status,
        reserved_usd=rec.reserved_usd,
    )
    db.add(row)
    try:
        await (db.commit() if commit else db.flush())
    except IntegrityError:
        # lost the race on the unique idempotency key: the other write is the record
        await db.rollback()
        if rec.idempotency_key:
            dup = (
                await db.execute(
                    select(ModelCall).where(ModelCall.idempotency_key == rec.idempotency_key)
                )
            ).scalar_one_or_none()
            if dup is not None:
                return dup
        raise
    return row


async def write_retrieval_trace(
    db: AsyncSession, rec: RetrievalTraceRecord, *, commit: bool = True
) -> RetrievalTrace:
    row = RetrievalTrace(
        learner_id=rec.learner_id,
        session_id=rec.session_id,
        collection=rec.collection,
        query=rec.query,
        filters_json=rec.filters,
        bm25_scores_json=rec.bm25_scores,
        vector_scores_json=rec.vector_scores,
        fused_json=rec.fused,
        reranked_json=rec.reranked,
        reranker_id=rec.reranker_id,
        chunk_ids_json=rec.chunk_ids,
        flagged_patterns_json=rec.flagged_patterns,
        latency_ms=rec.latency_ms,
    )
    db.add(row)
    await (db.commit() if commit else db.flush())
    return row


async def write_tutor_trace(
    db: AsyncSession, rec: TutorTraceRecord, *, commit: bool = True
) -> TutorTrace:
    row = TutorTrace(
        learner_id=rec.learner_id,
        session_id=rec.session_id,
        turn_id=rec.turn_id,
        action=rec.action,
        prompt_version=rec.prompt_version,
        sections_json=rec.sections,
        dropped_json=rec.dropped,
        model_call_id=rec.model_call_id,
        retrieval_trace_id=rec.retrieval_trace_id,
        latency_ms=rec.latency_ms,
    )
    db.add(row)
    await (db.commit() if commit else db.flush())
    return row


async def model_calls_for_task(db: AsyncSession, task: str, limit: int = 20) -> list[ModelCall]:
    stmt = (
        select(ModelCall).where(ModelCall.task == task).order_by(ModelCall.ts.desc()).limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())
