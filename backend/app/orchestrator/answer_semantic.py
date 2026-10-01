"""Semantic candidates remain historical output, never exact-reuse authority."""

import math
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db import answer_vectors
from app.db.answer_memory import candidates
from app.db.models import TutorAnswer
from app.db.traces import ModelCallRecord, write_model_call
from app.models_ai.ollama import OllamaProvider
from app.orchestrator.answer_index import identity
from app.schemas.playground import PlaygroundRequest


async def retrieve(
    db: AsyncSession, settings: Settings, learner_id: str, body: PlaygroundRequest
) -> list[dict[str, str]]:
    stmt = candidates(learner_id, body)
    query = (body.learner_question or body.question).strip()[:2000]
    if stmt is None or not query:
        return []
    rows = list((await db.scalars(stmt.order_by(TutorAnswer.id.desc()).limit(256))).all())
    rows = [
        row
        for row in rows
        if not row.metadata_json.get("answer_memory")
        and not row.request_json.get("historical_answer")
    ]
    if not rows:
        return []
    spec, key = await identity(db, settings, learner_id)
    # Only embed the query. Missing answer vectors require the separate indexing path.
    from sqlalchemy import select

    from app.db.models import TutorAnswerVector

    dims = await db.scalar(
        select(TutorAnswerVector.vector_json)
        .where(
            TutorAnswerVector.learner_id == learner_id,
            TutorAnswerVector.model_key == key,
            TutorAnswerVector.answer_id.in_([row.id for row in rows]),
        )
        .limit(1)
    )
    if not isinstance(dims, list) or not dims:
        return []
    cached = await answer_vectors.load(db, learner_id, [row.id for row in rows], key, len(dims))
    if not cached:
        return []
    fingerprints = {row.id: row.fingerprint for row in rows}
    snapshots = {
        row.id: {
            "answer_id": row.id,
            "saved_at": row.created_at,
            "question": str(
                row.request_json.get("learner_question") or row.request_json.get("question") or ""
            )[:400],
            "excerpt": row.text[:1200],
        }
        for row in rows
    }
    await db.commit()
    started = time.perf_counter()
    ok = False
    try:
        vector = (await OllamaProvider(settings.ollama_host).embed(spec, [query]))[0]
        if not answer_vectors.valid(vector) or len(vector) != len(dims):
            raise ValueError("Invalid query embedding")
        ok = True
    finally:
        await write_model_call(
            db,
            ModelCallRecord(
                provider=spec.provider,
                model=spec.model,
                registry_id=spec.registry_id,
                task="embed",
                learner_id=learner_id,
                latency_ms=round((time.perf_counter() - started) * 1000),
                ok=ok,
                outcome="ok" if ok else "error",
                metadata={"task": "answer_query"},
            ),
        )
    # Recheck visibility/fingerprint after inference, before returning any candidate.
    current = await answer_vectors.load(db, learner_id, list(cached), key, len(vector))
    refreshed = await db.scalars(
        stmt.where(TutorAnswer.id.in_(list(current))).execution_options(populate_existing=True)
    )
    allowed = {row.id for row in refreshed if row.fingerprint == fingerprints[row.id]}
    current = {id_: value for id_, value in current.items() if id_ in allowed}

    def unit(values: list[float]) -> list[float]:
        # Scale first: finite tiny/huge vectors must not underflow/overflow their norm.
        scale = max(abs(value) for value in values)
        scaled = [value / scale for value in values]
        norm = math.sqrt(sum(value * value for value in scaled))
        return [value / norm for value in scaled]

    query_unit = unit(vector)
    ranked = sorted(
        (
            (sum(x * y for x, y in zip(query_unit, unit(values), strict=True)), id_)
            for id_, values in current.items()
        ),
        reverse=True,
    )
    # Similarity threshold is only a conservative relevance filter, not confidence/truth.
    return [snapshots[id_] for score, id_ in ranked[:2] if score >= 0.65]
