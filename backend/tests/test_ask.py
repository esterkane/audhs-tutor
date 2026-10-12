import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.errors import AppError
from app.db import ask_requests
from app.db.models import AskRequest, LearningEvent, Session, TutorAnswer, TutorTrace
from app.models_ai import registry
from app.models_ai.budget import Budget
from app.models_ai.gateway import ModelGateway
from app.models_ai.routing import Router
from app.orchestrator import ask
from app.schemas.ask import AskQuestion


@pytest.fixture
async def ready(db, learner):
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    return learner


def headers():
    return {"Idempotency-Key": str(uuid4())}


async def test_ask_without_session_saves_and_replays(client, db, ready, fake_local):
    body = {"question": "How does quantization work?"}
    key = headers()
    response = await client.post("/api/ask", json=body, headers=key)
    assert response.status_code == 200, response.text
    answer = response.json()
    again = await client.post("/api/ask", json=body, headers=key)
    assert again.json() == answer
    assert len(fake_local.calls) == 1
    trace = (await db.scalars(select(TutorTrace))).one()
    assert trace.session_id is None and trace.model_call_id
    assert trace.turn_id == answer["turn_id"]
    assert answer["source_status"] == "not_requested"
    assert "not fact-checked" in answer["source_note"]
    assert await db.scalar(select(func.count()).select_from(Session)) == 0
    assert await db.scalar(select(func.count()).select_from(LearningEvent)) == 0
    assert await db.scalar(select(func.count()).select_from(TutorAnswer)) == 1
    saved = await db.get(TutorAnswer, answer["answer_id"])
    assert saved.session_id is None and saved.metadata_json["origin_status"] == "unknown"
    conflict = await client.post("/api/ask", json={"question": "Different work"}, headers=key)
    assert conflict.status_code == 409 and len(fake_local.calls) == 1
    suggestions = await client.get(
        "/api/answers", params={"q": "quanti", "question_prefix": True, "suggestions": True}
    )
    assert [a["id"] for a in suggestions.json()["items"]] == [answer["answer_id"]]


async def test_followup_uses_owned_ancestry_and_survives_deleted_parent_replay(
    client, db, ready, fake_local
):
    first = (
        await client.post("/api/ask", json={"question": "Explain precision"}, headers=headers())
    ).json()
    body = {"question": "Give me a concrete example", "parent_answer_id": first["answer_id"]}
    key = headers()
    second = await client.post("/api/ask", json=body, headers=key)
    assert second.status_code == 200, second.text
    assert second.json()["conversation_id"] == first["conversation_id"]
    assert second.json()["history_turns"] == 1
    assert [m.content for m in fake_local.calls[-1].messages][-3:] == [
        "Explain precision",
        first["text"],
        body["question"],
    ]
    await db.delete(await db.get(TutorAnswer, first["answer_id"]))
    await db.commit()
    replay = await client.post("/api/ask", json=body, headers=key)
    assert replay.json() == second.json() and len(fake_local.calls) == 2


async def test_wrong_owner_or_surface_does_not_create_claim(db, ready, fake_local):
    from app.db.models import LearnerProfile

    other = LearnerProfile(display_name="Other")
    db.add(other)
    await db.commit()
    row = TutorAnswer(
        learner_id=other.id,
        session_id=None,
        turn_id="other",
        surface="ask",
        request_json={"question": "private"},
        text="private",
        metadata_json={},
        fingerprint="x",
    )
    db.add(row)
    await db.commit()
    gateway = ModelGateway(db, Router("default"), {"ollama": fake_local}, Budget(0))
    with pytest.raises(AppError):
        await ask.respond(
            db,
            gateway,
            ready.id,
            AskQuestion(question="follow up", parent_answer_id=row.id),
            str(uuid4()),
        )
    assert not fake_local.calls
    assert await db.scalar(select(func.count()).select_from(AskRequest)) == 0


async def test_atomic_save_failure_leaves_no_answer_and_never_regenerates(
    db, ready, fake_local, monkeypatch
):
    learner_id = ready.id
    gateway = ModelGateway(db, Router("default"), {"ollama": fake_local}, Budget(0))

    async def fail(*args, **kwargs):
        raise RuntimeError("receipt failed")

    monkeypatch.setattr(ask_requests, "complete", fail)
    key = str(uuid4())
    body = AskQuestion(question="Explain a byte")
    with pytest.raises(RuntimeError, match="receipt failed"):
        await ask.respond(db, gateway, learner_id, body, key)
    assert await db.scalar(select(func.count()).select_from(TutorAnswer)) == 0
    assert await db.scalar(select(func.count()).select_from(TutorTrace)) == 0
    with pytest.raises(AppError, match="still running"):
        await ask.respond(db, gateway, learner_id, body, key)
    assert len(fake_local.calls) == 1


async def test_concurrent_duplicate_claims_have_one_winner(session_factory, ready):
    key = str(uuid4())
    payload = {"question": "One question"}

    async def claim():
        async with session_factory() as db:
            try:
                return await ask_requests.claim(db, ready.id, key, payload)
            except AppError as exc:
                return exc.code

    results = await asyncio.gather(claim(), claim())
    assert len([r for r in results if isinstance(r, tuple)]) == 1
    assert "request_unresolved" in results


async def test_stream_returns_saved_result_without_session(client, db, ready):
    response = await client.post(
        "/api/ask/stream", json={"question": "Explain binary"}, headers=headers()
    )
    assert response.status_code == 200
    assert "event: token" in response.text and "event: done" in response.text
    assert await db.scalar(select(func.count()).select_from(TutorAnswer)) == 1
    assert await db.scalar(select(func.count()).select_from(Session)) == 0


async def test_ask_receipts_export_and_wipe_are_owner_scoped(db, learner, db_path):
    import sqlite3

    from app.db.models import LearnerProfile
    from app.db.portability import export_learner, wipe_learner

    other = LearnerProfile(display_name="Other")
    db.add(other)
    await db.commit()
    owner_id, other_id = learner.id, other.id
    for owner in (owner_id, other_id):
        await ask_requests.claim(db, owner, str(uuid4()), {"question": "Saved intent"})
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        exported = export_learner(conn, owner_id)
        assert len(exported["ask_request"]) == 1
        assert exported["ask_request"][0]["learner_id"] == owner_id
        assert wipe_learner(conn, owner_id)["ask_request"] == 1
        assert len(export_learner(conn, other_id)["ask_request"]) == 1


def test_ask_downgrade_preserves_unresolved_receipts(tmp_path):
    import sqlite3

    from alembic import command
    from app.db.migrate import alembic_config, upgrade_to_head

    path = tmp_path / "ask-migration.db"
    url = f"sqlite:///{path}"
    upgrade_to_head(url)
    with sqlite3.connect(path) as conn:
        conn.execute(
            "INSERT INTO ask_request "
            "(id, learner_id, request_key, fingerprint, created_at) VALUES (?,?,?,?,?)",
            ("receipt", "owner", "request", "fingerprint", "2026-10-12"),
        )
    with pytest.raises(RuntimeError, match="Cannot discard Ask request receipts"):
        command.downgrade(alembic_config(url), "d1a07a70f6ac")
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT id FROM ask_request").fetchone() == ("receipt",)
        conn.execute("DELETE FROM ask_request")
    command.downgrade(alembic_config(url), "d1a07a70f6ac")
    upgrade_to_head(url)


def test_trace_downgrade_refuses_to_erase_sessionless_history(tmp_path):
    import sqlite3

    from alembic import command
    from app.db.migrate import alembic_config, upgrade_to_head

    path = tmp_path / "trace-migration.db"
    url = f"sqlite:///{path}"
    upgrade_to_head(url)
    with sqlite3.connect(path) as conn:
        conn.execute(
            "INSERT INTO tutor_trace (id, learner_id, turn_id, ts, action, prompt_version, "
            "sections_json, dropped_json, latency_ms) VALUES (?,?,?,?,?,?,?,?,?)",
            ("trace", "owner", "turn", "2026-10-12", "ask_explain", "v1", "{}", "[]", 0),
        )
    with pytest.raises(RuntimeError, match="session-independent tutor traces"):
        command.downgrade(alembic_config(url), "1b86eae1d303")
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT id FROM tutor_trace").fetchone() == ("trace",)
