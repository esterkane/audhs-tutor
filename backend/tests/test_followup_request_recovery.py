import asyncio

from sqlalchemy import func, select

from app.db.models import LearnerProfile, LearningEvent, ModelCall, TutorAnswer
from app.models_ai.registry import seed_defaults


async def setup(client, db):
    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    owner = (await client.get("/api/learner/me")).json()["id"]
    other = LearnerProfile(display_name="Other")
    db.add(other)
    await db.commit()
    for identity, learner in [("parent", owner), ("another", owner), ("foreign", other.id)]:
        db.add(
            TutorAnswer(
                id=identity,
                learner_id=learner,
                turn_id=identity,
                surface="playground",
                request_json={"question": "Why groups?"},
                text="Compare representation",
                metadata_json={},
                fingerprint=identity,
            )
        )
    await db.commit()
    return {"session_id": session["id"], "question": "Explain why."}


async def test_followup_lost_response_replay_is_parent_scoped(client, db, fake_local):
    body = await setup(client, db)
    headers = {"Idempotency-Key": "af041eed-cc4c-4512-887d-9c9159ec5d22"}
    first = await client.post("/api/answers/parent/followup", json=body, headers=headers)
    assert first.status_code == 200, first.text
    events = await db.scalar(select(func.count()).select_from(LearningEvent))
    calls = await db.scalar(select(func.count()).select_from(ModelCall))
    row = await db.get(TutorAnswer, first.json()["answer_id"])
    assert row.metadata_json["parent_answer_id"] == "parent"
    second = await client.post("/api/answers/parent/followup", json=body, headers=headers)
    assert second.json() == first.json()
    assert len(fake_local.calls) == 1
    assert await db.scalar(select(func.count()).select_from(ModelCall)) == calls
    assert await db.scalar(select(func.count()).select_from(LearningEvent)) == events
    for parent, status in [("another", 409), ("foreign", 404), ("missing", 404)]:
        assert (
            await client.post(f"/api/answers/{parent}/followup", json=body, headers=headers)
        ).status_code == status
    assert (
        await client.post(
            "/api/answers/parent/followup", json={**body, "question": "Changed"}, headers=headers
        )
    ).status_code == 409
    await client.post(f"/api/sessions/{body['session_id']}/end", json={})
    replay = await client.post("/api/answers/parent/followup", json=body, headers=headers)
    assert replay.json() == first.json()
    assert len(fake_local.calls) == 1


async def test_concurrent_followups_and_feedback_changes_do_not_regenerate(
    client, db, fake_local, monkeypatch
):
    from app.orchestrator import playground

    body = await setup(client, db)
    headers = {"Idempotency-Key": "770b3e81-86df-4f44-a65a-83c7c7d028b4"}
    entered, release = asyncio.Event(), asyncio.Event()
    original = playground.respond

    async def wait(*args, **kwargs):
        entered.set()
        await release.wait()
        return await original(*args, **kwargs)

    monkeypatch.setattr(playground, "respond", wait)
    pending = asyncio.create_task(
        client.post("/api/answers/parent/followup", json=body, headers=headers)
    )
    await asyncio.wait_for(entered.wait(), timeout=5)
    try:
        duplicate = await client.post("/api/answers/parent/followup", json=body, headers=headers)
        assert duplicate.status_code == 409
        assert duplicate.json()["error"]["code"] == "request_unresolved"
    finally:
        release.set()
    reply = await pending
    assert reply.status_code == 200
    feedback = await client.put(
        "/api/answers/parent/feedback",
        json={"verdict": "incorrect", "note": "Changed report", "hidden": False, "revision": 0},
    )
    assert feedback.status_code == 200, feedback.text
    replay = await client.post("/api/answers/parent/followup", json=body, headers=headers)
    assert replay.json() == reply.json()
    assert len(fake_local.calls) == 1
