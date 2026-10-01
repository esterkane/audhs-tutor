from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models import ModelCall, TutorAnswer, TutorAnswerFeedback, TutorAnswerVector
from app.models_ai.provider import ModelSpec
from app.orchestrator import answer_index


async def test_population_is_bounded_cached_filtered_and_logged(
    client: AsyncClient, db: AsyncSession, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    owner = (await client.get("/api/learner/me")).json()["id"]
    for identifier in ["a-memory", "b-hidden", "c-good", "d-good"]:
        db.add(
            TutorAnswer(
                id=identifier,
                learner_id=owner,
                turn_id=identifier,
                surface="playground",
                text="Retain proportions",
                request_json={"question": "How?"},
                fingerprint=identifier,
                metadata_json={"answer_memory": [{"answer_id": "old"}]}
                if identifier == "a-memory"
                else {},
            )
        )
    await db.flush()
    db.add(TutorAnswerFeedback(learner_id=owner, answer_id="b-hidden", hidden=True))
    await db.commit()

    async def identity(*args):  # type: ignore[no-untyped-def]
        return ModelSpec(registry_id="local", provider="ollama", model="local"), "digest:v1"

    calls = []

    async def embed(self, spec, texts):  # type: ignore[no-untyped-def]
        assert not db.in_transaction()
        calls.append(texts)
        return [[1.0, 0.0] for _ in texts]

    monkeypatch.setattr(answer_index, "identity", identity)
    monkeypatch.setattr(answer_index.OllamaProvider, "embed", embed)
    assert (await answer_index.populate(db, Settings(), owner, limit=1))["indexed"] == 1
    assert (await answer_index.populate(db, Settings(), owner, limit=1))["indexed"] == 1
    assert (await answer_index.populate(db, Settings(), owner, limit=1))["indexed"] == 0
    assert len(calls) == 2
    assert await db.scalar(select(func.count()).select_from(TutorAnswerVector)) == 2
    assert await db.scalar(select(func.count()).select_from(ModelCall)) == 2
    assert (await answer_index.populate(db, Settings(), owner, limit=1, rebuild=True))[
        "indexed"
    ] == 1
    assert len(calls) == 3


async def test_failed_embedding_is_logged_without_cache_entries(client, db, monkeypatch):  # type: ignore[no-untyped-def]
    import pytest

    owner = (await client.get("/api/learner/me")).json()["id"]
    db.add(
        TutorAnswer(
            id="failed",
            learner_id=owner,
            turn_id="failed",
            surface="playground",
            text="Reply",
            request_json={},
            metadata_json={},
            fingerprint="failed",
        )
    )
    await db.commit()

    async def identity(*args):  # type: ignore[no-untyped-def]
        return ModelSpec(registry_id="local", provider="ollama", model="local"), "v1"

    async def broken(*args):  # type: ignore[no-untyped-def]
        raise ValueError("Synthetic provider failure")

    monkeypatch.setattr(answer_index, "identity", identity)
    monkeypatch.setattr(answer_index.OllamaProvider, "embed", broken)
    with pytest.raises(ValueError):
        await answer_index.populate(db, Settings(), owner)
    assert await db.scalar(select(func.count()).select_from(TutorAnswerVector)) == 0
    call = await db.scalar(select(ModelCall))
    assert not call.ok and call.outcome == "error"


async def test_stale_last_write_does_not_hold_transaction_across_batches(client, db, monkeypatch):  # type: ignore[no-untyped-def]
    from sqlalchemy import update

    owner = (await client.get("/api/learner/me")).json()["id"]
    for i in range(17):
        db.add(
            TutorAnswer(
                id=f"a{i:02}",
                learner_id=owner,
                turn_id=f"a{i:02}",
                surface="playground",
                text="Reply",
                request_json={},
                metadata_json={},
                fingerprint=f"f{i}",
            )
        )
    await db.commit()

    async def identity(*args):  # type: ignore[no-untyped-def]
        return ModelSpec(registry_id="local", provider="ollama", model="local"), "v1"

    calls = 0

    async def embed(self, spec, texts):  # type: ignore[no-untyped-def]
        nonlocal calls
        assert not db.in_transaction()
        calls += 1
        if calls == 1:
            await db.execute(
                update(TutorAnswer).where(TutorAnswer.id == "a15").values(fingerprint="changed")
            )
            await db.commit()
        return [[1.0, 0.0] for _ in texts]

    monkeypatch.setattr(answer_index, "identity", identity)
    monkeypatch.setattr(answer_index.OllamaProvider, "embed", embed)
    result = await answer_index.populate(db, Settings(), owner)
    assert calls == 2 and result["indexed"] == 16
    assert not db.in_transaction()
