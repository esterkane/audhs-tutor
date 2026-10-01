"""Explicit local answer-vector population; no course indexing or generation."""

import hashlib
import json
import time
from urllib.parse import urlparse

import httpx
from sqlalchemy import and_, func, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db import answer_vectors
from app.db.models import TutorAnswer, TutorAnswerFeedback, TutorAnswerVector
from app.db.traces import ModelCallRecord, write_model_call
from app.models_ai import registry
from app.models_ai.ollama import OllamaProvider
from app.models_ai.provider import ModelSpec, TaskClass
from app.models_ai.routing import Router

FORMAT_VERSION = 1


async def identity(db: AsyncSession, settings: Settings, learner_id: str) -> tuple[ModelSpec, str]:
    if urlparse(settings.ollama_host).hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Answer embeddings require a loopback Ollama host")
    route = await Router(settings.routing_profile).resolve(
        db, TaskClass.EMBED, learner_id=learner_id
    )
    spec = await registry.get_spec(db, route.registry_id)
    if spec.provider != "ollama":
        raise ValueError("Answer embeddings require an installed local Ollama model")
    async with httpx.AsyncClient(timeout=5) as client:
        response = await client.get(settings.ollama_host.rstrip("/") + "/api/tags")
        response.raise_for_status()
    names = {spec.model, spec.model + ":latest"}
    digest = next(
        (
            item.get("digest")
            for item in response.json().get("models", [])
            if item.get("name") in names or item.get("model") in names
        ),
        None,
    )
    if not isinstance(digest, str) or not digest:
        raise ValueError("Installed embedding model digest unavailable")
    key = hashlib.sha256(
        json.dumps([FORMAT_VERSION, spec.registry_id, spec.model, digest]).encode()
    ).hexdigest()
    return spec, key


async def populate(
    db: AsyncSession,
    settings: Settings,
    learner_id: str,
    *,
    limit: int = 100,
    rebuild: bool = False,
) -> dict[str, int]:
    if not 1 <= limit <= 1000:
        raise ValueError("Index limit must be 1..1000")
    spec, key = await identity(db, settings, learner_id)
    excluded = select(TutorAnswerFeedback.answer_id).where(
        TutorAnswerFeedback.learner_id == learner_id,
        TutorAnswerFeedback.hidden.is_(True)
        | TutorAnswerFeedback.verdict.in_(["incorrect", "outdated"]),
    )
    cached = (
        select(TutorAnswerVector.answer_id)
        .where(
            TutorAnswerVector.learner_id == learner_id,
            TutorAnswerVector.model_key == key,
            TutorAnswerVector.answer_fingerprint == TutorAnswer.fingerprint,
        )
        .correlate(TutorAnswer)
    )
    rows = list(
        (
            await db.scalars(
                select(TutorAnswer)
                .where(
                    TutorAnswer.learner_id == learner_id,
                    TutorAnswer.id.not_in(excluded),
                    true() if rebuild else TutorAnswer.id.not_in(cached),
                    func.coalesce(
                        func.json_array_length(TutorAnswer.metadata_json["answer_memory"]), 0
                    )
                    == 0,
                    TutorAnswer.request_json["historical_answer"].as_string().is_(None),
                    or_(
                        TutorAnswer.surface == "playground",
                        and_(
                            TutorAnswer.surface == "tutor",
                            TutorAnswer.metadata_json["teaching_contract_key"]
                            .as_string()
                            .is_not(None),
                            TutorAnswer.request_json["conversation_lang"].as_string().is_(None),
                        ),
                    ),
                )
                .order_by(TutorAnswer.id)
                .limit(limit)
            )
        ).all()
    )
    pending = [
        (
            row.id,
            row.fingerprint,
            str(
                row.request_json.get("learner_question")
                or row.request_json.get("question")
                or row.request_json.get("text")
                or ""
            )[:2000]
            + "\n"
            + row.text[:4000],
        )
        for row in rows
        if not row.metadata_json.get("answer_memory")
        and not row.request_json.get("historical_answer")
    ]
    # Resolve/read first, then release the transaction before local inference.
    await db.commit()
    written = 0
    provider = OllamaProvider(settings.ollama_host)
    for start in range(0, len(pending), 16):
        batch = pending[start : start + 16]
        began = time.perf_counter()
        ok = False
        try:
            vectors = await provider.embed(spec, [item[2] for item in batch])
            if (
                len(vectors) != len(batch)
                or len({len(v) for v in vectors}) != 1
                or any(not answer_vectors.valid(vector) for vector in vectors)
            ):
                raise ValueError("Invalid embedding response")
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
                    latency_ms=round((time.perf_counter() - began) * 1000),
                    ok=ok,
                    outcome="ok" if ok else "error",
                    metadata={"task": "answer_index", "batch_size": len(batch)},
                ),
            )
        for (answer_id, fingerprint, _), vector in zip(batch, vectors, strict=True):
            written += await answer_vectors.put(db, learner_id, answer_id, fingerprint, key, vector)
        # A skipped stale/deleted answer leaves a read transaction; release it before inference.
        await db.commit()
    return {"selected": len(rows), "indexed": written, "skipped": len(rows) - written}
