"""Observability writers: tutor_trace, retrieval_trace, model_call. No trace = bug."""

from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ModelCall, RetrievalTrace, TutorTrace


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


class RetrievalTraceRecord(BaseModel):
    collection: str
    query: str
    filters: dict[str, Any] = Field(default_factory=dict)
    bm25_scores: dict[str, float] = Field(default_factory=dict)
    vector_scores: dict[str, float] = Field(default_factory=dict)
    fused: dict[str, float] = Field(default_factory=dict)
    reranked: dict[str, float] | None = None
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
    )
    db.add(row)
    await (db.commit() if commit else db.flush())
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


async def hosted_spend_since(db: AsyncSession, since_iso: str) -> float:
    """Sum of model_call.cost_usd for hosted providers since a UTC ISO timestamp (budget.py)."""
    stmt = select(func.coalesce(func.sum(ModelCall.cost_usd), 0.0)).where(
        ModelCall.ts >= since_iso, ModelCall.cost_usd > 0
    )
    return float((await db.execute(stmt)).scalar_one())


async def model_calls_for_task(db: AsyncSession, task: str, limit: int = 20) -> list[ModelCall]:
    stmt = (
        select(ModelCall).where(ModelCall.task == task).order_by(ModelCall.ts.desc()).limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())
