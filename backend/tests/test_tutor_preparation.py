"""Readiness must never become inference, hosted work, or a session dependency."""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import BackgroundTasks
from sqlalchemy import func, select

from app.api.tutor_preparation import schedule_preparation
from app.db.models import AssessmentAttempt, CompetencyEvidence, ModelCall, TutorAnswer
from app.models_ai.ollama import OllamaProvider
from app.models_ai.provider import ModelSpec
from app.models_ai.registry import seed_defaults


@pytest.mark.parametrize("remote", [False, True])
async def test_preload_uses_empty_local_request_and_rejects_cloud_alias(monkeypatch, remote):
    calls = []

    async def handle(request):
        calls.append((request.url.path, json.loads(request.content)))
        if request.url.path == "/api/show":
            return httpx.Response(
                200,
                json={
                    "model_info": {"general.architecture": "test"},
                    **({"remote_host": "https://upstream.example"} if remote else {}),
                },
            )
        return httpx.Response(200, json={"done": True, "message": {"content": ""}})

    original = httpx.AsyncClient
    monkeypatch.setattr(
        "app.models_ai.ollama.httpx.AsyncClient",
        lambda **kw: original(transport=httpx.MockTransport(handle), **kw),
    )
    loaded = await OllamaProvider("http://127.0.0.1:11434", keep_alive_s=300).preload(
        ModelSpec(registry_id="local", provider="ollama", model="alias")
    )
    assert loaded is not remote
    assert calls[0] == ("/api/show", {"model": "alias"})
    assert calls[1:] == (
        [] if remote else [("/api/chat", {"model": "alias", "stream": False, "keep_alive": 300})]
    )


@pytest.mark.parametrize(
    "host,provider,keep_alive",
    [
        ("https://remote.example", "ollama", 300),
        ("http://localhost:11434", "openai", 300),
        ("http://localhost:11434", "ollama", 0),
    ],
)
async def test_preload_skips_without_contacting_transport(monkeypatch, host, provider, keep_alive):
    def forbidden(**kwargs):
        raise AssertionError("No HTTP client should be opened")

    monkeypatch.setattr("app.models_ai.ollama.httpx.AsyncClient", forbidden)
    assert not await OllamaProvider(host, keep_alive_s=keep_alive).preload(
        ModelSpec(registry_id="selected", provider=provider, model="model")
    )


async def test_session_delivered_before_preparation_without_learning_writes(client, db, fake_local):
    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "gemma3:12b"})
    app = client._transport.app
    delivered = False

    async def observe(scope, receive, send):
        async def record(message):
            nonlocal delivered
            if message["type"] == "http.response.body":
                delivered = True
            await send(message)

        await app(scope, receive, record)

    client._transport.app = observe
    provider = OllamaProvider("http://localhost:11434")

    async def load(spec):
        assert delivered, "Session must not wait for weights to load"
        return True

    provider.preload = AsyncMock(side_effect=load)
    app.state.providers["ollama"] = provider
    response = await client.post("/api/sessions", json={"mode": "steady", "energy": 3})
    assert response.status_code == 201
    provider.preload.assert_awaited_once()
    row = (await db.scalars(select(ModelCall))).one()
    assert row.task == "model_preload" and row.session_id == response.json()["id"]
    assert row.tokens_in == row.tokens_out == 0 and row.cost_usd == 0
    assert row.metadata_json["for_task"] == "explain_simple"
    for model in (AssessmentAttempt, CompetencyEvidence, TutorAnswer):
        assert await db.scalar(select(func.count()).select_from(model)) == 0
    assert fake_local.calls == []


@pytest.mark.parametrize("scenario", ["disabled", "hosted", "ended", "failure", "duplicate"])
async def test_optional_preparation_guards_and_failure_isolation(client, db, settings, scenario):
    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "gemma3:12b", "hosted"})
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    owner = (await client.get("/api/learner/me")).json()["id"]
    app = client._transport.app
    provider = OllamaProvider("http://localhost:11434")
    provider.preload = AsyncMock(
        side_effect=RuntimeError("offline") if scenario == "failure" else None, return_value=True
    )
    app.state.providers["ollama"] = provider
    if scenario == "disabled":
        app.state.settings.ollama_prepare_on_session_start = False
    if scenario == "hosted":
        # Resolve explicitly below; the registry ID is verified by the defaults.
        from app.db.models import LearnerPreference, ModelRegistry

        hosted = await db.scalar(
            select(ModelRegistry.id).where(
                ModelRegistry.runtime == "hosted", ModelRegistry.status == "ready"
            )
        )
        assert hosted
        existing = await db.scalar(
            select(LearnerPreference).where(
                LearnerPreference.learner_id == owner,
                LearnerPreference.key == "routing.explain_simple",
            )
        )
        if existing:
            existing.value_json = hosted
        else:
            db.add(
                LearnerPreference(
                    learner_id=owner,
                    key="routing.explain_simple",
                    value_json=hosted,
                    origin="explicit",
                )
            )
        await db.commit()
    if scenario == "ended":
        await client.post(f"/api/sessions/{session['id']}/end", json={})
    background = BackgroundTasks()
    request = SimpleNamespace(app=app)
    schedule_preparation(request, background, app.state.settings, owner, session["id"])
    if scenario == "duplicate":

        async def held_load(spec):
            await asyncio.sleep(0.02)
            return True

        provider.preload.side_effect = held_load
        second = BackgroundTasks()
        schedule_preparation(request, second, app.state.settings, owner, session["id"])
        assert not app.state.tutor_preparation_pending
        await asyncio.gather(background(), second())
    else:
        await background()
    assert not getattr(app.state, "tutor_preparation_pending", set())
    assert provider.preload.await_count == (1 if scenario in {"failure", "duplicate"} else 0)
    assert (await client.get(f"/api/sessions/{session['id']}")).status_code == 200


async def test_failed_response_delivery_does_not_block_later_preparation(client, db):
    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "gemma3:12b"})
    app = client._transport.app
    provider = OllamaProvider("http://localhost:11434")
    provider.preload = AsyncMock(return_value=True)
    app.state.providers["ollama"] = provider

    async def disconnected(scope, receive, send):
        async def fail(message):
            if message["type"] == "http.response.body":
                raise RuntimeError("Response delivery lost")
            await send(message)

        await app(scope, receive, fail)

    client._transport.app = disconnected
    with pytest.raises(RuntimeError, match="Response delivery lost"):
        await client.post("/api/sessions", json={"mode": "steady", "energy": 3})
    provider.preload.assert_not_awaited()
    assert not app.state.tutor_preparation_pending
    client._transport.app = app
    response = await client.post("/api/sessions", json={"mode": "steady", "energy": 3})
    assert response.status_code == 201
    provider.preload.assert_awaited_once()


async def test_explicit_resume_prepares_without_changing_saved_session(client, db):
    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "gemma3:12b"})
    saved = (await client.post("/api/sessions", json={})).json()
    app = client._transport.app
    provider = OllamaProvider("http://localhost:11434")
    delivered = False

    async def load(spec):
        assert delivered
        return True

    provider.preload = AsyncMock(side_effect=load)
    app.state.providers["ollama"] = provider
    before = (await client.get(f"/api/sessions/{saved['id']}")).json()
    await client.get("/api/sessions/current")
    provider.preload.assert_not_awaited()

    async def observe(scope, receive, send):
        async def record(message):
            nonlocal delivered
            if message["type"] == "http.response.body":
                delivered = True
            await send(message)

        await app(scope, receive, record)

    client._transport.app = observe
    response = await client.post(f"/api/sessions/{saved['id']}/prepare")
    assert response.status_code == 204 and not response.content
    provider.preload.assert_awaited_once()
    assert (await client.get(f"/api/sessions/{saved['id']}")).json() == before
    for model in (AssessmentAttempt, CompetencyEvidence, TutorAnswer):
        assert await db.scalar(select(func.count()).select_from(model)) == 0


@pytest.mark.parametrize(
    "scenario,status", [("missing", 404), ("other_owner", 404), ("ended", 409)]
)
async def test_resume_rejects_invalid_session_without_loading(client, db, scenario, status):
    from app.db.models import LearnerProfile, Session

    saved = (await client.post("/api/sessions", json={})).json()
    session_id = saved["id"]
    if scenario == "missing":
        session_id = "not-a-session"
    elif scenario == "ended":
        await client.post(f"/api/sessions/{session_id}/end", json={})
    else:
        other = LearnerProfile(display_name="Other learner")
        db.add(other)
        await db.flush()
        session = await db.get(Session, session_id)
        session.learner_id = other.id
        await db.commit()
    provider = OllamaProvider("http://localhost:11434")
    provider.preload = AsyncMock(return_value=True)
    client._transport.app.state.providers["ollama"] = provider
    assert (await client.post(f"/api/sessions/{session_id}/prepare")).status_code == status
    provider.preload.assert_not_awaited()
