from sqlalchemy import func, select

from app.db.models import WorkspaceRequest
from app.models_ai.registry import seed_defaults


async def test_stale_lesson_rejected_before_claim_or_model(client, db, fake_local):
    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    calls = len(fake_local.calls)
    response = await client.post(
        "/api/playground/tutor",
        json={
            "session_id": session["id"],
            "exercise": "Example",
            "code": "",
            "lesson_origin": {"skill_id": "different-skill"},
        },
        headers={"Idempotency-Key": "1dfad3ea-1911-40e7-a024-1093d1a8c009"},
    )
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "lesson_context_changed"
    assert len(fake_local.calls) == calls
    assert await db.scalar(select(func.count()).select_from(WorkspaceRequest)) == 0


async def test_completed_replay_survives_lesson_change_but_new_request_does_not(
    client, db, fake_local
):
    from sqlalchemy import update

    from app.db.models import SessionCheckpoint
    from app.kernel.session import load_checkpoint

    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    from app.db.models import SkillNode

    db.add(
        SkillNode(
            id="lesson-origin-skill", slug="lesson-origin-skill", title="Example", domain="coding"
        )
    )
    await db.execute(
        update(SessionCheckpoint)
        .where(SessionCheckpoint.session_id == session["id"])
        .values(packet_json={"skill_id": "lesson-origin-skill"})
    )
    await db.commit()
    checkpoint = await load_checkpoint(db, session["id"])
    body = {
        "session_id": session["id"],
        "exercise": "Example",
        "code": "",
        "lesson_origin": {"skill_id": checkpoint["skill_id"]},
    }
    headers = {"Idempotency-Key": "16ef997b-f989-470b-aa79-bc47a5749b31"}
    first = await client.post("/api/playground/tutor", json=body, headers=headers)
    assert first.status_code == 200, first.text
    calls = len(fake_local.calls)
    await db.execute(
        update(SessionCheckpoint)
        .where(SessionCheckpoint.session_id == session["id"])
        .values(packet_json={"skill_id": "changed"})
    )
    await db.commit()
    replay = await client.post("/api/playground/tutor", json=body, headers=headers)
    assert replay.status_code == 200, replay.text
    assert replay.json() == first.json()
    fresh = await client.post("/api/playground/tutor", json=body)
    assert fresh.status_code == 409
    assert len(fake_local.calls) == calls


async def test_lesson_changed_during_saved_lookup_does_not_reach_model(
    client, db, fake_local, monkeypatch
):
    from sqlalchemy import update

    from app.db.models import SessionCheckpoint
    from app.kernel.session import load_checkpoint
    from app.orchestrator import playground

    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    from app.db.models import SkillNode

    db.add(
        SkillNode(
            id="lesson-origin-skill", slug="lesson-origin-skill", title="Example", domain="coding"
        )
    )
    await db.execute(
        update(SessionCheckpoint)
        .where(SessionCheckpoint.session_id == session["id"])
        .values(packet_json={"skill_id": "lesson-origin-skill"})
    )
    await db.commit()
    checkpoint = await load_checkpoint(db, session["id"])

    async def changed(lookup_db, *args):
        await lookup_db.execute(
            update(SessionCheckpoint)
            .where(SessionCheckpoint.session_id == session["id"])
            .values(packet_json={"skill_id": "changed"})
        )
        await lookup_db.flush()
        return []

    monkeypatch.setattr(playground, "retrieve", changed)
    response = await client.post(
        "/api/playground/tutor",
        json={
            "session_id": session["id"],
            "exercise": "Example",
            "code": "",
            "lesson_origin": {"skill_id": checkpoint["skill_id"]},
        },
    )
    assert response.status_code == 409, response.text
    assert not fake_local.calls


def test_absent_origin_preserves_old_payload_and_stays_out_of_prompt():
    from app.orchestrator.playground import messages
    from app.schemas.playground import PlaygroundRequest

    old = PlaygroundRequest(session_id="session", exercise="Example", code="")
    assert "lesson_origin" not in old.model_dump(mode="json")
    linked = old.model_copy(update={"lesson_origin": {"skill_id": "private-origin-marker"}})
    assert "private-origin-marker" not in str(messages(linked))
