"""Regression coverage for the owner's session-clarity report; no live learner data."""

from pathlib import Path

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.kernel import memory, skill_graph
from app.kernel.seed import load_seed
from app.models_ai import registry
from app.voice.tts import FakeTts

SEED = Path(__file__).resolve().parents[2] / "seeds" / "attention"


async def test_empty_area_never_falls_back_or_creates_session(
    client: AsyncClient, db: AsyncSession
) -> None:
    await load_seed(db, SEED)
    await client.put("/api/preferences", json={"key": "goal.area", "value": "python-draft-only"})
    assert (await client.get("/api/skills")).json()["next_skill_id"] is None
    before = list((await db.execute(select(models.Session.id))).scalars())
    response = await client.post("/api/sessions", json={})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "no_active_lesson"
    assert list((await db.execute(select(models.Session.id))).scalars()) == before


async def test_scope_is_snapshot_and_saved_lesson_choice_is_explicit(
    client: AsyncClient, db: AsyncSession
) -> None:
    await load_seed(db, SEED)
    me = (await client.get("/api/learner/me")).json()
    a = await skill_graph.get_node_by_slug(db, "vec-dot-product")
    b = await skill_graph.get_node_by_slug(db, "softmax")
    assert a and b
    a.course, b.course = "Course A", "Course B"
    await db.commit()
    for node in (a, b):
        await memory.ensure_item(db, me["id"], node.id, "recall", {"q": node.title})
    await client.put("/api/preferences", json={"key": "goal.course", "value": "Course A"})
    s = (await client.post("/api/sessions", json={})).json()
    assert s["state"]["skill_id"] == a.id and s["due_reviews"] == 1
    await client.put("/api/preferences", json={"key": "goal.course", "value": "Course B"})
    due = (await client.get("/api/review/due", params={"session_id": s["id"], "all": True})).json()
    assert {i["skill_id"] for i in due["items"]} == {a.id}
    saved = (await client.post("/api/sessions", json={"skill_id": a.id})).json()
    assert saved["checkpoint"]["scope_skill_ids"] == [a.id]
    assert next(x for x in saved["plan"] if x["type"] == "new_material")["node_ids"] == [a.id]


async def test_optional_confidence_and_stop_without_recap(
    client: AsyncClient, db: AsyncSession
) -> None:
    await load_seed(db, SEED)
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    s = (await client.post("/api/sessions", json={})).json()
    item = (await client.get("/api/assess/next", params={"session_id": s["id"]})).json()["item"]
    assert item["confidence_required"] is False
    a = await db.get(models.Assessment, item["id"])
    assert a
    response = await client.post(
        "/api/assess/attempt",
        json={
            "session_id": s["id"],
            "assessment_id": a.id,
            "answer": str(a.item_json["answer"]),
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["confidence_pre"] is None
    assert response.json()["calibration"] == "confidence not supplied"
    ix = next(i for i, b in enumerate(s["plan"]) if b["type"] == "new_material")
    await client.post("/api/plan/blocks/start", json={"session_id": s["id"], "index": ix})
    end = await client.post(f"/api/sessions/{s['id']}/end", json={})
    assert end.status_code == 200 and end.json()["ended_at"]
    assert end.json()["energy_after"] is None
    assert end.json()["state"]["block_status"] == "ended"
    await client.post(f"/api/sessions/{s['id']}/end", json={})
    events = list(
        (
            await db.execute(
                select(models.LearningEvent).where(
                    models.LearningEvent.session_id == s["id"], models.LearningEvent.verb == "ended"
                )
            )
        ).scalars()
    )
    assert len(events) == 1 and events[0].result_json["self_report"] is None


async def test_material_marks_are_reversible_self_report(
    client: AsyncClient, db: AsyncSession
) -> None:
    await load_seed(db, SEED)
    skill = await skill_graph.get_node_by_slug(db, "vec-dot-product")
    assert skill
    for status in ("later", "clear", None):
        response = await client.put(f"/api/skills/{skill.id}/mark", json={"status": status})
        assert response.status_code == 200 and response.json()["status"] == status
        marks = (await client.get("/api/preferences")).json()["values"]["learning.material_marks"]
        assert marks.get(skill.id) == status
    assert not list((await db.execute(select(models.CompetencyEvidence))).scalars())
    assert not list((await db.execute(select(models.ReviewItem))).scalars())


async def test_read_aloud_without_microphone_logs_tts_and_bounds_text(
    client: AsyncClient, db: AsyncSession
) -> None:
    app = client._transport.app  # type: ignore[attr-defined]
    tts = FakeTts()
    app.state.voice_overrides = {"tts": tts, "stt": None}
    response = await client.post("/api/voice/speak", json={"text": "A small worked example."})
    assert response.status_code == 200 and response.json()["pcm16_b64"]
    assert tts.spoken == ["A small worked example."]
    assert (await client.post("/api/voice/speak", json={"text": "x" * 1201})).status_code == 422
    calls = list((await db.execute(select(models.ModelCall))).scalars())
    assert len(calls) == 1 and calls[0].task == "tts"
    assert calls[0].metadata_json["purpose"] == "lesson-read-aloud"
    app.state.voice_overrides = {"tts": FakeTts(fail_times=1)}
    assert (await client.post("/api/voice/speak", json={"text": "Try again."})).status_code == 503


async def test_assisted_review_is_not_logged_as_unaided_easy(
    client: AsyncClient, db: AsyncSession
) -> None:
    await load_seed(db, SEED)
    me = (await client.get("/api/learner/me")).json()
    skill = await skill_graph.get_node_by_slug(db, "vec-dot-product")
    assert skill
    item, _ = await memory.ensure_item(db, me["id"], skill.id, "recall", {"q": "Recall"})
    s = (await client.post("/api/sessions", json={})).json()
    response = await client.post(
        f"/api/review/{item.id}", json={"session_id": s["id"], "rating": 4, "hint_count": 1}
    )
    assert response.status_code == 200
    event = (
        await db.execute(
            select(models.LearningEvent).where(models.LearningEvent.verb == "reviewed")
        )
    ).scalar_one()
    assert event.result_json["rating"] == 2 and event.result_json["hint_count"] == 1
