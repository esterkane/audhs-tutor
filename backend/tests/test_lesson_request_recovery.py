import asyncio
import json
import logging
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from app.db.models import LearningEvent, ModelCall, SessionCheckpoint, TutorAnswer
from app.kernel.seed import load_seed
from app.models_ai.registry import seed_defaults

SEED = Path(__file__).resolve().parents[2] / "seeds" / "attention"


async def setup(client, db):
    await load_seed(db, SEED)
    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "gemma3:12b"})
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    return {"session_id": session["id"], "text": "Explain groups", "action": "explain"}


def events(response):
    return [
        (block.splitlines()[0][7:], json.loads(block.splitlines()[1][6:]))
        for block in response.text.strip().split("\n\n")
    ]


@pytest.mark.parametrize("first_stream", [False, True])
@pytest.mark.parametrize("partial", [False, True])
async def test_lost_lesson_reply_replays_across_transports_without_progress_writes(
    client, db, fake_local, first_stream, partial, caplog
):
    caplog.set_level(logging.INFO, logger="uvicorn.error.tutor_timing")
    body = await setup(client, db)
    if partial:
        fake_local.fail_after_words = 1
    headers = {"Idempotency-Key": "5499ffbe-aae6-4c1e-a5f1-c330cf2c7897"}
    first = await client.post(
        "/api/tutor/stream" if first_stream else "/api/tutor/turn", json=body, headers=headers
    )
    assert first.status_code == 200, first.text
    done = dict(events(first))["done"] if first_stream else first.json()
    assert done["outcome"] == ("partial" if partial else "ok")
    before = {
        table.__name__: await db.scalar(select(func.count()).select_from(table))
        for table in (LearningEvent, ModelCall, TutorAnswer)
    }
    checkpoint = await db.scalar(
        select(SessionCheckpoint.packet_json).where(
            SessionCheckpoint.session_id == body["session_id"]
        )
    )
    calls = len(fake_local.calls)
    stream = await client.post("/api/tutor/stream", json=body, headers=headers)
    replay = dict(events(stream))
    diagnostic = json.loads(
        [
            r.getMessage().removeprefix("tutor_timing ")
            for r in caplog.records
            if r.name == "uvicorn.error.tutor_timing"
        ][-1]
    )
    assert "replay_started" in diagnostic["marks_ms"]
    assert "first_text_ready" not in diagnostic["marks_ms"]
    assert "turn_started" not in diagnostic["marks_ms"]
    assert diagnostic["body_completed"] is True
    assert replay["done"] == done
    assert replay["meta"]["turn_id"] == done["turn_id"]
    assert replay["meta"]["replayed"] is True
    if first_stream:
        assert dict(events(first))["meta"]["replayed"] is False
    assert replay["token"]["text"] == done["text"]
    buffered = await client.post("/api/tutor/turn", json=body, headers=headers)
    assert buffered.json() == done
    assert len(fake_local.calls) == calls
    for table in (LearningEvent, ModelCall, TutorAnswer):
        assert await db.scalar(select(func.count()).select_from(table)) == before[table.__name__]
    assert (
        await db.scalar(
            select(SessionCheckpoint.packet_json).where(
                SessionCheckpoint.session_id == body["session_id"]
            )
        )
        == checkpoint
    )
    conflict = await client.post(
        "/api/tutor/turn", json={**body, "text": "Different"}, headers=headers
    )
    assert conflict.status_code == 409
    await client.post(f"/api/sessions/{body['session_id']}/end", json={})
    ended = await client.post("/api/tutor/turn", json=body, headers=headers)
    assert ended.json() == done


async def test_concurrent_stream_retry_reports_unresolved(client, db, monkeypatch):
    from app.orchestrator.tutor import TutorTurn

    body = await setup(client, db)
    headers = {"Idempotency-Key": "cb32a8eb-f892-4caa-a5b8-6fda511f2606"}
    entered, release = asyncio.Event(), asyncio.Event()
    original = TutorTurn.run

    async def delayed(self, request):
        entered.set()
        await release.wait()
        async for item in original(self, request):
            yield item

    monkeypatch.setattr(TutorTurn, "run", delayed)
    first = asyncio.create_task(client.post("/api/tutor/stream", json=body, headers=headers))
    await asyncio.wait_for(entered.wait(), timeout=5)
    try:
        duplicate = await client.post("/api/tutor/stream", json=body, headers=headers)
        assert duplicate.status_code == 409
        assert duplicate.json()["error"]["code"] == "request_unresolved"
    finally:
        release.set()
    assert dict(events(await first))["done"]["outcome"] == "ok"


async def test_failed_terminal_save_keeps_received_text_and_does_not_restart(
    client, db, fake_local, monkeypatch
):
    from app.db import workspace_requests

    body = await setup(client, db)
    headers = {"Idempotency-Key": "f0074f32-cde6-4dda-a45e-f6c17730ae94"}

    async def fail(*args, **kwargs):
        raise OperationalError("update", {}, Exception("save failed"))

    monkeypatch.setattr(workspace_requests, "complete", fail)
    first = await client.post("/api/tutor/stream", json=body, headers=headers)
    output = events(first)
    assert any(kind == "token" for kind, _ in output)
    assert output[-1][0] == "error"
    assert "Nothing was changed" not in output[-1][1]["message"]
    calls = len(fake_local.calls)
    repeated = await client.post("/api/tutor/stream", json=body, headers=headers)
    assert repeated.status_code == 409
    assert len(fake_local.calls) == calls


@pytest.mark.parametrize("endpoint", ["/api/tutor/turn", "/api/tutor/stream"])
async def test_default_lesson_kind_retains_legacy_recovery_identity(
    client, db, fake_local, endpoint
):
    from app.db.models import WorkspaceRequest
    from app.db.workspace_requests import request_fingerprint
    from app.schemas.tutor import TurnRequest

    body = await setup(client, db)
    key = "c3b879da-d57c-4e36-8885-7a24612256b4"
    headers = {"Idempotency-Key": key}
    response = await client.post(endpoint, json=body, headers=headers)
    assert response.status_code == 200
    legacy = {
        "surface": "lesson_turn",
        **TurnRequest(**body).model_dump(
            mode="json", exclude={"assessment_answer_id", "explanation_kind"}
        ),
    }
    stored = await db.scalar(select(WorkspaceRequest).where(WorkspaceRequest.request_key == key))
    assert stored.fingerprint == request_fingerprint(legacy)
    calls = len(fake_local.calls)
    replay = await client.post(
        endpoint, json={**body, "explanation_kind": "lesson"}, headers=headers
    )
    assert replay.status_code == 200 and len(fake_local.calls) == calls
    conflict = await client.post(
        endpoint, json={**body, "explanation_kind": "follow_up"}, headers=headers
    )
    assert conflict.status_code == 409 and len(fake_local.calls) == calls
