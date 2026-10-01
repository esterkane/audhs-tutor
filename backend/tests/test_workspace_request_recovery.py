"""Transport retry must not repeat inference (separate from optional semantic reuse)."""

from sqlalchemy import func, select

from app.db.models import TutorAnswer
from app.models_ai.registry import seed_defaults


async def test_lost_response_retries_original_turn_without_generation(client, db, fake_local):
    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    body = {"session_id": session["id"], "exercise": "Example", "code": "x=1", "question": "Why?"}
    headers = {"Idempotency-Key": "55c74d39-a9b4-4a5c-9eb0-e9df8e70ad68"}
    first = await client.post("/api/playground/tutor", json=body, headers=headers)
    assert first.status_code == 200, first.text
    calls = len(fake_local.calls)
    # Client loses this successful response, then repeats the same logical request.
    second = await client.post("/api/playground/tutor", json=body, headers=headers)
    assert second.status_code == 200, second.text
    assert second.json() == first.json()
    assert len(fake_local.calls) == calls
    assert await db.scalar(select(func.count()).select_from(TutorAnswer)) == 1


async def test_concurrent_claim_conflict_and_interrupted_work(client, db, fake_local, monkeypatch):
    import asyncio

    from app.orchestrator import playground

    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    body = {"session_id": session["id"], "exercise": "Example", "code": "x=1"}
    headers = {"Idempotency-Key": "b010ab83-a313-40b2-9106-2cc21d813eac"}
    entered, release = asyncio.Event(), asyncio.Event()
    original = playground.respond

    async def delayed(*args, **kwargs):
        entered.set()
        await release.wait()
        return await original(*args, **kwargs)

    monkeypatch.setattr(playground, "respond", delayed)
    first = asyncio.create_task(client.post("/api/playground/tutor", json=body, headers=headers))
    await asyncio.wait_for(entered.wait(), timeout=5)
    try:
        duplicate = await client.post("/api/playground/tutor", json=body, headers=headers)
        assert duplicate.status_code == 409
        assert duplicate.json()["error"]["code"] == "request_unresolved"
        conflict = await client.post(
            "/api/playground/tutor", json={**body, "code": "x=2"}, headers=headers
        )
        assert conflict.status_code == 409
        assert conflict.json()["error"]["code"] == "request_conflict"
        assert not fake_local.calls
    finally:
        release.set()
    assert (await first).status_code == 200
    assert len(fake_local.calls) == 1


async def test_cancelled_claim_cannot_generate_again(client, db, fake_local, monkeypatch):
    import asyncio

    from app.orchestrator import playground

    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    body = {"session_id": session["id"], "exercise": "Example", "code": "x=1"}
    headers = {"Idempotency-Key": "f314da80-3a7e-4126-a422-9d2a94940308"}

    async def interrupted(*args, **kwargs):
        raise asyncio.CancelledError()

    monkeypatch.setattr(playground, "respond", interrupted)
    import pytest

    # Starlette's middleware represents cancellation before a response as this error.
    with pytest.raises(RuntimeError, match="No response returned"):
        await client.post("/api/playground/tutor", json=body, headers=headers)
    retry = await client.post("/api/playground/tutor", json=body, headers=headers)
    assert retry.status_code == 409
    assert retry.json()["error"]["code"] == "request_unresolved"
    assert not fake_local.calls


async def test_completed_claim_survives_new_connection_and_ended_session(
    db, learner, session_factory
):
    import pytest

    from app.core.errors import AppError
    from app.db import workspace_requests
    from app.db.models import LearnerProfile, Session

    session = Session(learner_id=learner.id, mode="steady", energy=3)
    other = LearnerProfile(display_name="Other")
    db.add_all([session, other])
    await db.commit()
    identity, result = await workspace_requests.claim(
        db, learner.id, session.id, "key", {"work": 1}
    )
    assert result is None
    await workspace_requests.complete(db, learner.id, identity, {"text": "Original"})
    session.ended_at = "2026-10-01T23:00:00Z"
    await db.commit()
    async with session_factory() as fresh:
        assert await workspace_requests.claim(
            fresh, learner.id, session.id, "key", {"work": 1}
        ) == (identity, {"text": "Original"})
        with pytest.raises(KeyError):
            await workspace_requests.claim(fresh, other.id, session.id, "key", {"work": 1})
        with pytest.raises(AppError):
            await workspace_requests.claim(fresh, learner.id, session.id, "new", {"work": 1})
    await db.delete(session)
    await db.commit()
    with pytest.raises(KeyError):
        await workspace_requests.claim(db, learner.id, session.id, "key", {"work": 1})


async def test_racing_connections_claim_only_once(db, learner, session_factory):
    import asyncio

    from app.core.errors import AppError
    from app.db import workspace_requests
    from app.db.models import Session, WorkspaceRequest

    session = Session(learner_id=learner.id, mode="steady", energy=3)
    db.add(session)
    await db.commit()

    async def attempt():
        async with session_factory() as connection:
            return await workspace_requests.claim(connection, learner.id, session.id, "same", {})

    results = await asyncio.gather(attempt(), attempt(), return_exceptions=True)
    assert sum(isinstance(result, tuple) for result in results) == 1
    failures = [result for result in results if isinstance(result, AppError)]
    assert len(failures) == 1 and failures[0].code == "request_unresolved"
    assert await db.scalar(select(func.count()).select_from(WorkspaceRequest)) == 1


async def test_failed_final_persistence_never_repeats_generation(
    client, db, fake_local, monkeypatch
):
    import pytest
    from sqlalchemy.exc import OperationalError

    from app.db import workspace_requests

    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    body = {"session_id": session["id"], "exercise": "Example", "code": "x=1"}
    headers = {"Idempotency-Key": "f6228ad0-4c9c-423a-bc96-96bfe927bb96"}

    async def fail(*args, **kwargs):
        raise OperationalError("update", {}, Exception("disk unavailable"))

    monkeypatch.setattr(workspace_requests, "complete", fail)
    with pytest.raises(OperationalError):
        await client.post("/api/playground/tutor", json=body, headers=headers)
    calls = len(fake_local.calls)
    assert calls == 1
    retry = await client.post("/api/playground/tutor", json=body, headers=headers)
    assert retry.status_code == 409
    assert len(fake_local.calls) == calls
    assert await db.scalar(select(func.count()).select_from(TutorAnswer)) == 1
