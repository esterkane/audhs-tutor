from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.db.models import ModelCall
from app.models_ai import manage, registry
from app.models_ai.bench import summarize
from app.models_ai.embedding_bench import bench_embedding
from app.models_ai.provider import ModelSpec, ProviderError


async def embedding_row(db):
    return await registry.upsert(
        db,
        {
            "id": "embedding-fixture",
            "display_name": "Embedding fixture",
            "source": "ollama_library",
            "repo_id": "embedding-fixture",
            "file_or_tag": "embedding-fixture",
            "runtime": "ollama",
            "role": "embed",
            "status": "ready",
            "context_len": 4096,
        },
    )


async def test_manage_bench_uses_embedding_retrieval_not_chat(db, monkeypatch):
    row = await embedding_row(db)
    provider = SimpleNamespace(
        embed=AsyncMock(
            side_effect=[[[1.0, 0.0], [0.0, 1.0], [-1.0, -1.0]], [[1.0, 0.0], [0.0, 1.0]]]
        )
    )
    monkeypatch.setattr(manage, "build_providers", lambda settings: {"ollama": provider})
    result = await manage.bench(db, Settings(), row.id)
    assert result["kind"] == "embedding" and result["dimensions"] == 2
    assert result["retrieval_top1"] == {"passed": 2, "total": 2}
    assert (await registry.get_row(db, row.id)).benchmark_json == result
    calls = (await db.scalars(select(ModelCall))).all()
    assert len(calls) == 2 and all(c.ok and c.task == "embed" for c in calls)
    assert {c.metadata_json["purpose"] for c in calls} == {"documents", "queries"}
    assert "retrieval 2/2" in summarize(result)


async def test_embedding_bench_records_failed_attempt_and_does_not_qualify(db, monkeypatch):
    row = await embedding_row(db)
    provider = SimpleNamespace(embed=AsyncMock(side_effect=ProviderError("unavailable")))
    monkeypatch.setattr(manage, "build_providers", lambda settings: {"ollama": provider})
    with pytest.raises(ProviderError):
        await manage.bench(db, Settings(), row.id)
    assert (await registry.get_row(db, row.id)).benchmark_json is None
    calls = (await db.scalars(select(ModelCall))).all()
    assert len(calls) == 1 and not calls[0].ok and calls[0].outcome == "error"


async def test_embedding_bench_rejects_hosted_without_contact(db):
    provider = SimpleNamespace(embed=AsyncMock())
    with pytest.raises(ValueError, match="local"):
        await bench_embedding(
            db, provider, ModelSpec(registry_id="hosted", provider="openai", model="hosted")
        )
    provider.embed.assert_not_awaited()


async def test_embedding_bench_rejects_zero_vectors(db):
    row = await embedding_row(db)
    provider = SimpleNamespace(embed=AsyncMock(return_value=[[0.0, 0.0]] * 3))
    with pytest.raises(ProviderError):
        await bench_embedding(db, provider, await registry.get_spec(db, row.id))
    assert not (await db.scalar(select(ModelCall))).ok
