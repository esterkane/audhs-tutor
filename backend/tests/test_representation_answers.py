import asyncio
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from app.db.models import LearningEvent, TutorAnswer
from app.kernel import representations as krep
from app.kernel.seed import load_seed
from app.knowledge.reindex import load_chunks
from app.models_ai import registry
from app.orchestrator import representations as orep

SEED = Path(__file__).resolve().parents[2] / "seeds" / "attention"


async def setup(client, db, repo, provider):
    await load_seed(db, SEED)
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    await repo.upsert(await load_chunks(db))
    provider.text = "A volume knob is an analogy [1]. Try one example."
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    url = f"/api/objects/{session['next_skill']['id']}/representations/analogy"
    return session, url


async def test_representation_history_survives_cache_deletion(client, db, fake_repo, fake_local):
    session, url = await setup(client, db, fake_repo, fake_local)
    first = (await client.post(url, json={"session_id": session["id"]})).json()
    assert first["answer_id"] and not first["save_error"]
    events = await db.scalar(select(func.count()).select_from(LearningEvent))
    calls = len(fake_local.calls)
    again = (await client.post(url, json={"session_id": session["id"]})).json()
    assert again["answer_id"] == first["answer_id"] and again["cached"]
    assert await db.scalar(select(func.count()).select_from(TutorAnswer)) == 1
    assert await db.scalar(select(func.count()).select_from(LearningEvent)) == events
    await krep.invalidate(db, first["object_id"])
    detail = (await client.get("/api/answers/" + first["answer_id"])).json()
    assert detail["text"] == first["content"]
    assert detail["metadata"]["representation_id"] == first["representation_id"]
    assert detail["metadata"]["sources"] == first["source_snapshot"]
    assert detail["metadata"]["source_text_hashes"] == first["source_text_hashes"]
    found = (
        await client.get("/api/answers", params={"q": "volume knob", "surface": "representation"})
    ).json()
    assert [row["id"] for row in found["items"]] == [first["answer_id"]]
    assert len(fake_local.calls) == calls


@pytest.mark.parametrize("committed", [False, True])
async def test_representation_failed_save_recovers_without_generation(
    client, db, fake_repo, fake_local, monkeypatch, committed
):
    session, url = await setup(client, db, fake_repo, fake_local)
    original = orep.save_completed

    async def fail(connection, **snapshot):
        if committed:
            await original(connection, **snapshot)
        await connection.rollback()
        raise OperationalError("insert", {}, Exception("temporary"))

    monkeypatch.setattr(orep, "save_completed", fail)
    response = await client.post(url, json={"session_id": session["id"]})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["content"] and result["save_receipt"] and result["save_error"]
    calls = len(fake_local.calls)
    for _ in range(2):
        restored = await client.post(
            "/api/answers/recover-save", json={"receipt": result["save_receipt"]}
        )
        assert restored.status_code == 200, restored.text
    assert await db.scalar(select(func.count()).select_from(TutorAnswer)) == 1
    answer = await db.scalar(select(TutorAnswer))
    assert answer.text == result["content"]
    assert len(fake_local.calls) == calls


async def test_legacy_cache_saves_unknown_provenance_without_inference(
    client, db, fake_repo, fake_local
):
    session, url = await setup(client, db, fake_repo, fake_local)
    obj = await krep.object_for_skill(db, session["next_skill"]["id"])
    assert obj is not None
    await krep.store(db, obj.id, "analogy", "Old explanation [1].", model_call_id=None)
    calls = len(fake_local.calls)
    result = (await client.post(url, json={"session_id": session["id"]})).json()
    assert result["cached"] and result["answer_id"] and not result["provenance_available"]
    detail = (await client.get("/api/answers/" + result["answer_id"])).json()
    assert detail["metadata"]["provenance_available"] is False
    assert detail["metadata"]["sources"] == [] and detail["metadata"]["object_version"] is None
    assert len(fake_local.calls) == calls


async def test_concurrent_cached_deliveries_share_history(client, db, fake_repo, fake_local):
    session, url = await setup(client, db, fake_repo, fake_local)
    obj = await krep.object_for_skill(db, session["next_skill"]["id"])
    assert obj is not None
    await krep.store(db, obj.id, "analogy", "Already generated.", model_call_id=None)
    responses = await asyncio.gather(
        *[client.post(url, json={"session_id": session["id"]}) for _ in range(2)]
    )
    assert all(response.status_code == 200 for response in responses)
    assert responses[0].json()["answer_id"] == responses[1].json()["answer_id"]
    assert responses[0].json()["answer_id"]
    assert await db.scalar(select(func.count()).select_from(TutorAnswer)) == 1
    assert fake_local.calls == []


@pytest.mark.parametrize("prose_reference", [False, True])
async def test_representation_code_literals_do_not_cite_sources(
    client, db, fake_repo, fake_local, prose_reference
):
    session, url = await setup(client, db, fake_repo, fake_local)
    text = "Use `items[1]`.\n```python\nvalues = [1, 2]\n```\nThese values are literals."
    if prose_reference:
        text += " The source is [1]."
    fake_local.text = text
    response = await client.post(url, json={"session_id": session["id"]})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["content"] == text
    sources = result["source_snapshot"]
    assert sources and [s["cited"] for s in sources] == [
        prose_reference and i == 0 for i in range(len(sources))
    ]
    restored = (await client.get("/api/answers/" + result["answer_id"])).json()
    assert restored["text"] == text
    assert restored["metadata"]["sources"] == sources


@pytest.mark.parametrize(
    "tail",
    [
        "```python\nvalues = [1, 2]\nprint(values[1])\n```",
        "```sql\nSELECT 1 AS value;\n```",
        "1. Read the vector\n2. Compare matching components",
        r"$$q \cdot k = \sum_i q_i k_i$$",
    ],
)
async def test_complete_representation_tails_survive_delivery_cache_and_history(
    client, db, fake_repo, fake_local, tail
):
    session, url = await setup(client, db, fake_repo, fake_local)
    text = "Use the following complete example to inspect each requested result.\n" + tail
    fake_local.text = text
    first = (await client.post(url, json={"session_id": session["id"]})).json()
    assert first["content"] == text
    calls = len(fake_local.calls)
    again = (await client.post(url, json={"session_id": session["id"]})).json()
    assert again["cached"] and again["content"] == text and again["answer_id"] == first["answer_id"]
    restored = (await client.get("/api/answers/" + first["answer_id"])).json()
    assert restored["text"] == text
    assert len(fake_local.calls) == calls


async def test_old_generated_cache_refreshes_once_without_rewriting_saved_history(
    client, db, fake_repo, fake_local
):
    from app.db.models import Representation

    session, url = await setup(client, db, fake_repo, fake_local)
    old_text = "A previously generated introductory sentence without its example."
    fake_local.text = old_text
    first = (await client.post(url, json={"session_id": session["id"]})).json()
    row = await db.get(Representation, first["representation_id"])
    assert row is not None and row.model_call_id
    row.provenance_json = {
        key: value for key, value in row.provenance_json.items() if key != "delivery_contract"
    }
    await db.commit()
    calls = len(fake_local.calls)
    complete = "Use this complete example to inspect the result.\n```sql\nSELECT 1;\n```"
    fake_local.text = complete
    refreshed = (await client.post(url, json={"session_id": session["id"]})).json()
    assert refreshed["content"] == complete and not refreshed["cached"]
    assert refreshed["representation_id"] != first["representation_id"]
    assert len(fake_local.calls) == calls + 1
    old_saved = (await client.get("/api/answers/" + first["answer_id"])).json()
    assert old_saved["text"] == old_text
    again = (await client.post(url, json={"session_id": session["id"]})).json()
    assert again["cached"] and again["answer_id"] == refreshed["answer_id"]
    assert len(fake_local.calls) == calls + 1
