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
@pytest.mark.parametrize("context_len", [8192, 32768])
async def test_preload_uses_empty_local_request_and_rejects_cloud_alias(
    monkeypatch, remote, context_len
):
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
        ModelSpec(registry_id="local", provider="ollama", model="alias", context_len=context_len)
    )
    assert loaded is not remote
    assert calls[0] == ("/api/show", {"model": "alias"})
    assert calls[1:] == (
        []
        if remote
        else [
            (
                "/api/chat",
                {
                    "model": "alias",
                    "stream": False,
                    "keep_alive": 300,
                    "options": {"num_ctx": min(16384, context_len)},
                },
            )
        ]
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


@pytest.mark.parametrize(
    ("phase", "expected"),
    [("teach", "explain_simple"), ("assess", "grade_simple"), ("apply", "explain_simple")],
)
async def test_resume_prepares_task_for_saved_phase_without_inference(
    client, db, fake_local, phase, expected
):
    from app.db.models import Session
    from app.kernel import session as ksession

    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "gemma3:12b"})
    body = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    saved = await db.get(Session, body["id"])
    await ksession.save_checkpoint(db, saved, {"phase": phase})
    app = client._transport.app
    provider = OllamaProvider("http://localhost:11434")
    provider.preload = AsyncMock(return_value=True)
    app.state.providers["ollama"] = provider
    response = await client.post(f"/api/sessions/{saved.id}/prepare")
    assert response.status_code == 204
    provider.preload.assert_awaited_once()
    row = (await db.scalars(select(ModelCall).where(ModelCall.task == "model_preload"))).one()
    assert row.metadata_json["for_task"] == expected
    assert row.tokens_in == row.tokens_out == 0 and row.cost_usd == 0
    assert not fake_local.calls
    for model in (AssessmentAttempt, CompetencyEvidence, TutorAnswer):
        assert await db.scalar(select(func.count()).select_from(model)) == 0


@pytest.mark.parametrize(
    "scenario", ["ready", "disabled", "readonly", "foreign", "failure", "busy", "duplicate"]
)
async def test_research_readiness_does_not_generate_or_change_saved_work(client, db, scenario):
    from uuid import uuid4

    from app.api.tutor_preparation import schedule_research_preparation
    from app.db.models import CurriculumDraft

    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "gemma3:12b"})
    draft = (
        await client.post(
            "/api/knowledge-material/drafts",
            headers={"Idempotency-Key": str(uuid4())},
            json={"title": "Preparation test", "notes": "Keep this exact writing."},
        )
    ).json()
    owner = (await client.get("/api/learner/me")).json()["id"]
    app = client._transport.app
    provider = OllamaProvider("http://localhost:11434")
    provider.is_resident = AsyncMock(return_value=True)
    provider.preload = AsyncMock(
        side_effect=RuntimeError("offline") if scenario == "failure" else None, return_value=True
    )
    app.state.providers["ollama"] = provider
    if scenario == "disabled":
        app.state.settings.ollama_prepare_on_session_start = False
    if scenario == "busy":
        app.state.research_tutor_active = 1
    if scenario == "readonly":
        row = await db.get(CurriculumDraft, draft["id"])
        row.status = "rejected"
        await db.commit()
    background = BackgroundTasks()
    request = SimpleNamespace(app=app)
    schedule_research_preparation(
        request,
        background,
        app.state.settings,
        "foreign-owner" if scenario == "foreign" else owner,
        draft["id"],
    )
    if scenario == "duplicate":

        async def held(spec):
            await asyncio.sleep(0.02)
            return True

        provider.preload.side_effect = held
        second = BackgroundTasks()
        schedule_research_preparation(request, second, app.state.settings, owner, draft["id"])
        await asyncio.gather(background(), second())
        third = BackgroundTasks()
        schedule_research_preparation(request, third, app.state.settings, owner, draft["id"])
        await third()
    else:
        await background()
    assert provider.preload.await_count == (
        1 if scenario in {"ready", "failure", "duplicate"} else 0
    )
    assert not getattr(app.state, "research_preparation_pending", set())
    saved = await db.get(CurriculumDraft, draft["id"], populate_existing=True)
    assert (
        saved.version == draft["version"]
        and saved.payload_json["authoring"]["notes"] == "Keep this exact writing."
    )
    for model in (AssessmentAttempt, CompetencyEvidence, TutorAnswer):
        assert await db.scalar(select(func.count()).select_from(model)) == 0
    for row in (await db.scalars(select(ModelCall))).all():
        assert row.task == "model_preload" and row.tokens_in == row.tokens_out == row.cost_usd == 0


async def test_research_preparation_sends_response_before_loading(client, db):
    from uuid import uuid4

    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "gemma3:12b"})
    draft = (
        await client.post(
            "/api/knowledge-material/drafts",
            headers={"Idempotency-Key": str(uuid4())},
            json={"title": "Response first", "notes": "Saved source text"},
        )
    ).json()
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
        assert delivered
        return True

    provider.preload = AsyncMock(side_effect=load)
    app.state.providers["ollama"] = provider
    response = await client.post(f"/api/knowledge-material/drafts/{draft['id']}/prepare-tutor")
    assert response.status_code == 202
    provider.preload.assert_awaited_once()


@pytest.mark.parametrize("residency", [True, False, RuntimeError("unavailable")])
async def test_recent_research_preparation_recovers_eviction(client, db, residency):
    from uuid import uuid4

    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "gemma3:12b"})
    draft = (
        await client.post(
            "/api/knowledge-material/drafts",
            headers={"Idempotency-Key": str(uuid4())},
            json={"title": "Eviction", "notes": "Preserve source and history."},
        )
    ).json()
    provider = OllamaProvider("http://localhost:11434")
    provider.preload = AsyncMock(return_value=True)
    provider.is_resident = AsyncMock(
        side_effect=residency if isinstance(residency, Exception) else None,
        return_value=residency,
    )
    app = client._transport.app
    app.state.providers["ollama"] = provider
    url = f"/api/knowledge-material/drafts/{draft['id']}/prepare-tutor"
    assert (await client.post(url)).status_code == 202
    assert (await client.post(url)).status_code == 202
    provider.is_resident.assert_awaited_once()
    assert provider.preload.await_count == (1 if residency is True else 2)
    assert not app.state.research_preparation_pending


@pytest.mark.parametrize("resident", ["selected:latest", "other:latest", None])
async def test_residency_probe_is_local_readonly_and_handles_default_tag(monkeypatch, resident):
    calls = []

    async def handle(request):
        calls.append(request)
        return httpx.Response(200, json={"models": [{"name": resident}] if resident else []})

    original = httpx.AsyncClient

    def client(**kwargs):
        assert kwargs["trust_env"] is False and kwargs["follow_redirects"] is False
        return original(transport=httpx.MockTransport(handle), **kwargs)

    monkeypatch.setattr("app.models_ai.ollama.httpx.AsyncClient", client)
    provider = OllamaProvider("http://localhost:11434")
    spec = ModelSpec(registry_id="selected", provider="ollama", model="selected")
    assert await provider.is_resident(spec) is (resident == "selected:latest")
    assert len(calls) == 1 and calls[0].method == "GET" and calls[0].url.path == "/api/ps"


async def test_memory_results_delivered_before_tutor_restoration(
    client, db, fake_repo, monkeypatch
):
    from uuid import uuid4

    from app.models_ai.provider import ModelSpec

    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "gemma3:12b"})
    draft = (
        await client.post(
            "/api/knowledge-material/drafts",
            headers={"Idempotency-Key": str(uuid4())},
            json={"title": "Search readiness", "notes": "Preserve this source."},
        )
    ).json()
    monkeypatch.setattr(
        "app.knowledge.reindex.embed_spec",
        AsyncMock(
            return_value=ModelSpec(
                registry_id="fake",
                provider="fake",
                model="fake",
            )
        ),
    )
    monkeypatch.setattr("app.knowledge.reindex.build_repo", AsyncMock(return_value=fake_repo))
    monkeypatch.setattr("app.knowledge.personal_memory.search", AsyncMock(return_value=[]))
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
        assert delivered, "Search results must not wait for tutor weights"
        return True

    provider.preload = AsyncMock(side_effect=load)
    app.state.providers["ollama"] = provider
    response = await client.post(
        f"/api/knowledge-material/drafts/{draft['id']}/memories/search",
        json={"query": "evidence"},
    )
    assert response.status_code == 200 and response.json() == {"memories": []}
    provider.preload.assert_awaited_once()
    assert (await client.get("/api/curriculum/drafts")).json()["drafts"][0] == draft
