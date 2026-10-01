import asyncio
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from app.core.answer_recovery import AnswerRecovery
from app.core.errors import AppError
from app.db.models import ModelCall, TutorAnswer
from app.models_ai.registry import seed_defaults

SEED = Path(__file__).resolve().parents[2] / "seeds" / "attention"


def test_receipt_rejects_tampering_other_owner_expiry_and_restart(monkeypatch):
    recovery = AnswerRecovery()
    monkeypatch.setattr("app.core.answer_recovery.time.time", lambda: 100)
    token = recovery.issue({"learner_id": "one", "text": "Original answer"})
    assert token and recovery.read(token, "one")["text"] == "Original answer"
    for service, value, owner in [
        (recovery, token + "x", "one"),
        (recovery, token, "two"),
        (AnswerRecovery(), token, "one"),
        (recovery, "invalid", "one"),
    ]:
        with pytest.raises(AppError) as error:
            service.read(value, owner)
        assert error.value.http_status == 410
        assert "Original answer" not in str(error.value)
    monkeypatch.setattr("app.core.answer_recovery.time.time", lambda: 3700)
    with pytest.raises(AppError):
        recovery.read(token, "one")
    assert recovery.issue({"learner_id": "one", "text": "x" * 500000}) is None


@pytest.mark.parametrize("committed_before_error", [False, True])
async def test_save_retry_keeps_exact_answer_deduplicates_and_never_generates(
    client, db, fake_local, monkeypatch, committed_before_error
):
    from app.orchestrator import playground

    original = playground.save_completed
    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()

    async def fail(connection, **snapshot):
        if committed_before_error:
            await original(connection, **snapshot)
        await connection.rollback()
        raise OperationalError("insert", {}, Exception("temporary save failure"))

    monkeypatch.setattr(playground, "save_completed", fail)
    response = await client.post(
        "/api/playground/tutor",
        json={
            "session_id": session["id"],
            "exercise": "Example",
            "code": "x = 1",
            "question": "Why?",
        },
    )
    assert response.status_code == 200, response.text
    reply = response.json()
    assert reply["save_error"] and reply["save_receipt"] and not reply["answer_id"]
    calls = len(fake_local.calls)
    request = {"receipt": reply["save_receipt"]}
    first, second = await asyncio.gather(
        client.post("/api/answers/recover-save", json=request),
        client.post("/api/answers/recover-save", json=request),
    )
    assert first.status_code == second.status_code == 200, (first.text, second.text)
    assert first.json()["answer_id"] == second.json()["answer_id"]
    assert len(fake_local.calls) == calls
    row = await db.get(TutorAnswer, first.json()["answer_id"])
    assert row.text == reply["text"]
    assert row.turn_id == reply["turn_id"]
    assert row.request_json["question"] == "Why?"
    assert row.metadata_json["model"] == reply["model"]
    assert await db.scalar(select(func.count()).select_from(TutorAnswer)) == 1
    assert await db.scalar(select(func.count()).select_from(ModelCall)) == calls


async def test_deleted_session_cannot_be_restored_with_receipt(client, db):
    from app.db.models import Session

    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    row = await db.get(Session, session["id"])
    # Use an otherwise unused owned session so this is a save-authorization test, not a wipe test.
    spare = Session(learner_id=row.learner_id, mode="steady", energy=3)
    db.add(spare)
    await db.commit()
    token = client._transport.app.state.answer_recovery.issue(
        dict(
            learner_id=row.learner_id,
            session_id=spare.id,
            turn_id="lost",
            surface="tutor",
            request={},
            text="Original",
            metadata={},
        )
    )
    await db.delete(spare)
    await db.commit()
    response = await client.post("/api/answers/recover-save", json={"receipt": token})
    assert response.status_code == 404
    assert await db.scalar(select(func.count()).select_from(TutorAnswer)) == 0


@pytest.mark.parametrize("partial", [False, True])
async def test_lesson_recovery_requires_complete_output(
    client, db, fake_local, monkeypatch, partial
):

    from app.kernel.seed import load_seed
    from app.orchestrator import tutor

    await load_seed(db, SEED)
    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "gemma3:12b"})
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()

    async def fail(connection, **snapshot):
        await connection.rollback()
        raise OperationalError("insert", {}, Exception("save failed"))

    monkeypatch.setattr(tutor, "save_completed", fail)
    if partial:
        fake_local.text = "Partial explanation interrupted"
        fake_local.fail_after_words = 1
    response = await client.post(
        "/api/tutor/turn",
        json={"session_id": session["id"], "text": "Explain groups", "action": "explain"},
    )
    assert response.status_code == 200, response.text
    reply = response.json()
    if partial:
        assert reply["outcome"] == "partial" and reply["save_receipt"] is None
        assert await db.scalar(select(func.count()).select_from(TutorAnswer)) == 0
        return
    assert reply["outcome"] == "ok" and reply["save_receipt"] and reply["tutor_trace_id"]
    calls = len(fake_local.calls)
    saved = await client.post("/api/answers/recover-save", json={"receipt": reply["save_receipt"]})
    assert saved.status_code == 200, saved.text
    row = await db.get(TutorAnswer, saved.json()["answer_id"])
    assert row.surface == "tutor" and row.text == reply["text"]
    assert row.metadata_json["sources"] == reply["sources"]
    assert len(fake_local.calls) == calls
