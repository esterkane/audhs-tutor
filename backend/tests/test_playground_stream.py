import asyncio
import json
from uuid import uuid4

from fastapi import BackgroundTasks
from sqlalchemy import func, select

from app.api import playground as api
from app.db.models import AssessmentAttempt, ModelCall, TutorAnswer
from app.models_ai.registry import seed_defaults
from app.schemas.playground import PlaygroundRequest


async def test_stream_tokens_final_disclosures_and_original_identity_replay(client, db, fake_local):
    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "gemma3:12b"})
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    fake_local.text = "Keep the sample separate."
    body = {
        "session_id": session["id"],
        "intent": "explain",
        "exercise": "Explain data cleaning",
        "code": "",
        "output_stale": True,
        "output": "old output",
    }
    headers = {"Idempotency-Key": str(uuid4())}
    response = await client.post("/api/playground/tutor/stream", json=body, headers=headers)
    assert response.status_code == 200
    events = [
        (block.split("\n")[0][7:], json.loads(block.split("data: ")[1]))
        for block in response.text.strip().split("\n\n")
    ]
    assert events[0][0] == "token" and events[-1][0] == "done"
    final = events[-1][1]
    assert "supplied output is marked outdated" in final["text"]
    assert final["answer_id"]
    assert sum(1 for kind, _ in events if kind == "done") == 1
    replay = await client.post("/api/playground/tutor", json=body, headers=headers)
    assert replay.status_code == 200 and replay.json() == final
    assert await db.scalar(select(func.count()).select_from(ModelCall)) == 1
    assert await db.scalar(select(func.count()).select_from(TutorAnswer)) == 1
    assert await db.scalar(select(func.count()).select_from(AssessmentAttempt)) == 0


async def test_preview_precedes_completion_and_disconnect_cleans_worker(monkeypatch):
    stopped = asyncio.Event()

    async def answer(*args):
        try:
            await args[-1]("Early preview")
            await asyncio.Event().wait()
        finally:
            stopped.set()

    monkeypatch.setattr(api, "_answer", answer)
    response = await api.tutor_stream(
        PlaygroundRequest(session_id="s", intent="explain", exercise="Task", code=""),
        None,
        None,
        None,
        None,
        None,
        BackgroundTasks(),
        None,
    )
    iterator = response.body_iterator
    first = await asyncio.wait_for(anext(iterator), 1)
    assert b"Early preview" in first
    assert not stopped.is_set()
    await iterator.aclose()
    assert stopped.is_set()


async def test_stream_rejects_structured_intents_before_work(client):
    for intent in ["starter", "check_answer", "check_bins"]:
        response = await client.post(
            "/api/playground/tutor/stream",
            json={
                "session_id": "s",
                "intent": intent,
                "exercise": "Task",
                "code": "",
                "learner_answer": "My answer",
            },
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "buffered_intent"


async def test_actual_asgi_disconnect_awaits_worker_cleanup(monkeypatch):
    sent = asyncio.Event()
    cleaned = asyncio.Event()

    async def answer(*args):
        try:
            await args[-1]("Preview")
            await asyncio.Event().wait()
        finally:
            await asyncio.sleep(0.01)
            cleaned.set()

    monkeypatch.setattr(api, "_answer", answer)
    response = await api.tutor_stream(
        PlaygroundRequest(session_id="s", intent="explain", exercise="Task", code=""),
        None,
        None,
        None,
        None,
        None,
        BackgroundTasks(),
        None,
    )

    async def send(message):
        if message["type"] == "http.response.body" and message.get("body"):
            sent.set()

    async def receive():
        await sent.wait()
        return {"type": "http.disconnect"}

    await asyncio.wait_for(
        response({"type": "http", "asgi": {"spec_version": "2.3"}}, receive, send), 1
    )
    assert cleaned.is_set()


async def test_output_limit_keeps_preview_but_never_saves_a_complete_answer(
    client, db, fake_local, monkeypatch
):
    from app.models_ai.provider import StreamFinish

    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "gemma3:12b"})
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    original = fake_local.stream

    async def capped(*args, **kwargs):
        async for event in original(*args, **kwargs):
            yield event
        yield StreamFinish(reason="length")

    monkeypatch.setattr(fake_local, "stream", capped)
    body = {
        "session_id": session["id"],
        "intent": "explain",
        "exercise": "Explain this",
        "code": "",
    }
    headers = {"Idempotency-Key": str(uuid4())}
    response = await client.post("/api/playground/tutor/stream", json=body, headers=headers)
    assert "event: token" in response.text
    assert "tutor_output_limit" in response.text
    assert "event: done" not in response.text
    retry = await client.post("/api/playground/tutor/stream", json=body, headers=headers)
    assert "request_unresolved" in retry.text
    assert len(fake_local.calls) == 1
    assert await db.scalar(select(func.count()).select_from(TutorAnswer)) == 0
    assert await db.scalar(select(func.count()).select_from(AssessmentAttempt)) == 0
