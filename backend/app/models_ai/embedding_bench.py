"""Local embedding compatibility and bilingual retrieval smoke benchmark."""

import math
import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.traces import ModelCallRecord, write_model_call
from app.models_ai.provider import EmbeddingProvider, ModelSpec, ProviderError


async def bench_embedding(
    db: AsyncSession, provider: EmbeddingProvider, spec: ModelSpec
) -> dict[str, Any]:
    if spec.provider != "ollama":
        raise ValueError("Embedding benchmarks require an installed local Ollama model")
    documents = [
        "PostgreSQL row security policies filter rows; they do not supply missing SQL UPDATE privileges.",
        "After a serialization failure, retry the whole transaction including its reads and decisions.",
        "Kubernetes schedules Pods onto nodes according to their resource requests and constraints.",
    ]
    queries = [
        "Kann eine Zeilenrichtlinie fehlende UPDATE-Rechte ersetzen?",
        "Why must a serialization failure repeat the whole transaction?",
    ]
    results = []
    latencies = []
    for purpose, texts in [("documents", documents), ("queries", queries)]:
        started = time.perf_counter()
        ok, error = False, None
        try:
            vectors = await provider.embed(
                spec, spec.embedding_inputs(texts, query=purpose == "queries")
            )
            if len(vectors) != len(texts) or any(
                not vector
                or any(not math.isfinite(v) for v in vector)
                or sum(v * v for v in vector) <= 0
                for vector in vectors
            ):
                raise ProviderError("Invalid embedding benchmark vectors")
            if len({len(v) for v in vectors}) != 1:
                raise ProviderError("Inconsistent embedding benchmark dimensions")
            results.append(vectors)
            ok = True
        except BaseException as exc:
            error = type(exc).__name__
            raise
        finally:
            latency = round((time.perf_counter() - started) * 1000)
            latencies.append(latency)
            await write_model_call(
                db,
                ModelCallRecord(
                    provider=spec.provider,
                    model=spec.model,
                    registry_id=spec.registry_id,
                    task="embed",
                    tokens_in=sum(len(t) // 4 for t in texts),
                    usage_source="estimated",
                    latency_ms=latency,
                    ok=ok,
                    error=error,
                    outcome="ok" if ok else "error",
                    metadata={
                        "task": "embedding_benchmark",
                        "purpose": purpose,
                        "items": len(texts),
                    },
                ),
            )
    docs, question_vectors = results
    dimensions = len(docs[0])
    if any(len(v) != dimensions for v in question_vectors) or (
        spec.embedding is not None and dimensions != spec.embedding.dimensions
    ):
        raise ProviderError("Embedding benchmark dimensions do not match the model contract")

    def cosine(a: list[float], b: list[float]) -> float:
        return sum(x * y for x, y in zip(a, b, strict=True)) / math.sqrt(
            sum(x * x for x in a) * sum(y * y for y in b)
        )

    passed = sum(
        max(range(len(docs)), key=lambda j: cosine(query, docs[j])) == expected
        for expected, query in enumerate(question_vectors)
    )
    return {
        "kind": "embedding",
        "benchmarked_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "dimensions": dimensions,
        "documents": len(documents),
        "queries": len(queries),
        "latency_ms_median": sorted(latencies)[len(latencies) // 2],
        "retrieval_top1": {"passed": passed, "total": len(queries)},
    }
