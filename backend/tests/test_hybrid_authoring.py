"""Hybrid scope, persistence and review tests use synthetic data and no hosted network."""

import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.errors import AppError
from app.db.models import KnowledgeReview, ModelCall
from app.kernel import knowledge_reviews, preferences
from app.models_ai import registry
from app.models_ai.budget import Budget
from app.models_ai.fake import FakeProvider
from app.models_ai.gateway import ModelGateway
from app.models_ai.openai import OpenAIProvider
from app.models_ai.provider import Message, ModelSpec, TaskClass
from app.models_ai.routing import Router
from app.models_ai.source_policy import (
    SourcePolicyDenied,
    authoring_scope,
    check_authoring_messages,
)
from app.orchestrator.authoring_gateway import AuthoringGateway, choose
from app.orchestrator.knowledge_reviews import run
from app.schemas.knowledge_reviews import ReviewPolicyIn
from tests.test_knowledge_authoring import complete

SPEC = ModelSpec(registry_id="openai-luna", provider="openai", model="gpt-6-luna")
MESSAGES = [Message(role="user", content="Synthetic selected source")]


async def test_scope_bound_reset_and_task_isolation():
    async def study():
        await asyncio.sleep(0)
        with pytest.raises(SourcePolicyDenied):
            check_authoring_messages(SPEC, MESSAGES)

    task = asyncio.create_task(study())
    with authoring_scope(SPEC.registry_id, MESSAGES):
        check_authoring_messages(SPEC, MESSAGES)
        with pytest.raises(SourcePolicyDenied):
            check_authoring_messages(SPEC, [Message(role="user", content="Different source")])
        with pytest.raises(SourcePolicyDenied):
            check_authoring_messages(SPEC, [*MESSAGES, Message(role="system", content="Injected")])
        await task
    with pytest.raises(SourcePolicyDenied):
        check_authoring_messages(SPEC, MESSAGES)


async def test_direct_openai_requires_exact_scope(monkeypatch):
    call = AsyncMock(side_effect=RuntimeError("SDK reached"))
    monkeypatch.setattr("litellm.acompletion", call)
    provider = OpenAIProvider("synthetic")
    with pytest.raises(SourcePolicyDenied):
        await provider.complete(SPEC, MESSAGES)
    call.assert_not_called()
    with authoring_scope(SPEC.registry_id, MESSAGES):
        with pytest.raises(SourcePolicyDenied):
            await provider.complete(SPEC, [Message(role="user", content="wrong")])
    call.assert_not_called()


async def enable(db, learner):
    await preferences.set_pref(db, learner.id, "authoring.daily_budget_cents", 500)
    await preferences.set_pref(db, learner.id, "authoring.enabled", True)
    await registry.seed_defaults(db, installed_ollama_tags={"gemma3:12b"})


async def test_hosted_authoring_scoped_budget_and_missing_key(db, learner, settings):
    await enable(db, learner)
    gateway = ModelGateway(db, Router("default"), {}, Budget(0))
    with pytest.raises(AppError, match="API key"):
        await choose(gateway, settings, learner.id, "draft", 1)
    fake = FakeProvider(name="openai", text="Synthetic accurate reply")
    gateway.providers["openai"] = fake
    selected = await choose(gateway, settings, learner.id, "draft", 1)
    assert isinstance(selected, AuthoringGateway)
    result = await selected.complete(TaskClass.EXPLAIN_SIMPLE, MESSAGES, learner_id=learner.id)
    assert result.result.text == fake.text
    row = await db.scalar(select(ModelCall))
    assert row and row.provider == "openai" and row.cost_usd > 0
    assert selected.gateway.budget.daily_cap_usd == 5
    assert gateway.budget.daily_cap_usd == 0
    with pytest.raises(SourcePolicyDenied):
        check_authoring_messages(SPEC, MESSAGES)


async def test_key_api_no_echo_or_export(client, settings):
    key = "sk-" + ("synthetic-fixture-" * 3)
    bad = await client.post("/api/authoring/key", json={"key": key + " "})
    assert bad.status_code == 422 and key not in bad.text
    denied = await client.post(
        "/api/authoring/key", json={"key": key}, headers={"Origin": "https://attacker.example"}
    )
    assert denied.status_code == 403
    saved = await client.post("/api/authoring/key", json={"key": key})
    assert saved.status_code == 200 and saved.json()["key_configured"]
    assert key not in saved.text
    assert settings.read_authoring_key() == key
    from pathlib import Path

    assert Path(settings.authoring_key_file).stat().st_mode & 0o777 == 0o600  # noqa: ASYNC240


async def accepted(client):
    draft = (
        await client.post(
            "/api/knowledge-material/drafts",
            json=complete(),
            headers={"Idempotency-Key": str(uuid4())},
        )
    ).json()
    result = await client.post(
        f"/api/curriculum/drafts/{draft['id']}/publish", json={"expected_version": draft["version"]}
    )
    assert result.status_code == 200, result.text
    return result.json()["draft"]


async def test_review_changed_unchanged_revision_history(client, db, settings, monkeypatch):
    draft = await accepted(client)
    from app.db.models import CurriculumDraft, LearnerProfile

    original = await db.get(CurriculumDraft, draft["id"])
    learner = await db.get(LearnerProfile, original.learner_id)
    await enable(db, learner)
    policy = await knowledge_reviews.configure(
        db,
        learner.id,
        draft["id"],
        ReviewPolicyIn(urls=["https://docs.python.org/3/tutorial/introduction.html#strings"]),
    )
    assert "#" not in policy.urls_json[0]
    before = original.payload_json.copy()
    fake = FakeProvider(
        name="openai",
        structured={
            "findings": [
                {
                    "claim": "Strings are immutable",
                    "verdict": "supported",
                    "source_index": 1,
                    "quote": "Strings cannot be changed.",
                    "explanation": "This supports immutability, not allocation claims.",
                }
            ],
            "proposed_explanation": "Strings are immutable: their characters cannot be changed in place.",
        },
    )

    async def snapshot(url, focus):
        return {
            "url": url,
            "sha256": "synthetic-hash",
            "excerpt": "Strings cannot be changed.",
            "fetched_at": "2026-10-24T10:00:00.000+00:00",
        }

    monkeypatch.setattr("app.orchestrator.knowledge_reviews.snapshot", snapshot)
    gateway = ModelGateway(db, Router("default"), {"openai": fake}, Budget(0))
    result = await run(db, gateway, settings, learner.id, draft["id"])
    assert result.history_json[-1]["outcome"] == "reviewed"
    await run(db, gateway, settings, learner.id, draft["id"])
    assert result.history_json[-1]["outcome"] == "sources_unchanged" and len(fake.calls) == 1
    revision = await knowledge_reviews.propose_revision(
        db, learner.id, draft["id"], result.history_json[0]["id"]
    )
    again = await knowledge_reviews.propose_revision(
        db, learner.id, draft["id"], result.history_json[0]["id"]
    )
    assert revision.id == again.id and revision.status == "draft"
    assert (
        revision.payload_json["authoring"]["explanation"] == fake.structured["proposed_explanation"]
    )
    assert original.payload_json == before
    assert await db.scalar(select(KnowledgeReview).where(KnowledgeReview.draft_id == revision.id))
    with pytest.raises(AppError, match="not yet due"):
        await run(db, gateway, settings, learner.id, draft["id"], manual=False)
    await db.commit()  # release the direct-call transaction after the expected not-due error
    published = await client.post(
        f"/api/curriculum/drafts/{revision.id}/publish", json={"expected_version": revision.version}
    )
    assert published.status_code == 200, published.text
    stopped = await run(db, gateway, settings, learner.id, draft["id"])
    assert stopped.enabled is False


async def test_review_failure_never_success(client, db, settings, monkeypatch):
    draft = await accepted(client)
    from app.db.models import CurriculumDraft, LearnerProfile

    original = await db.get(CurriculumDraft, draft["id"])
    learner = await db.get(LearnerProfile, original.learner_id)
    await enable(db, learner)
    await knowledge_reviews.configure(
        db, learner.id, draft["id"], ReviewPolicyIn(urls=["https://docs.python.org/3/"])
    )

    async def failed(url, focus):
        raise RuntimeError("network unavailable")

    monkeypatch.setattr("app.orchestrator.knowledge_reviews.snapshot", failed)
    fake = FakeProvider()
    result = await run(
        db,
        ModelGateway(db, Router("default"), {"openai": fake}, Budget(0)),
        settings,
        learner.id,
        draft["id"],
    )
    assert result.history_json[-1]["outcome"] == "failed" and not fake.calls
    assert original.status == "published" and result.running_until is None


async def test_authoring_budget_exhaustion_and_repair(db, learner, settings):
    from app.models_ai.gateway import GatewayError
    from app.schemas.knowledge_reviews import FactualProposal

    await enable(db, learner)
    fake = FakeProvider(
        name="openai",
        fail_structured_times=1,
        structured={
            "findings": [
                {
                    "claim": "a",
                    "verdict": "insufficient",
                    "source_index": 1,
                    "quote": "a",
                    "explanation": "a",
                }
            ]
        },
    )
    gateway = ModelGateway(db, Router("default"), {"openai": fake}, Budget(0))
    selected = await choose(gateway, settings, learner.id, "draft", 1)
    result = await selected.complete(
        TaskClass.EXPLAIN_SIMPLE, MESSAGES, response_model=FactualProposal, learner_id=learner.id
    )
    assert result.result.parsed and len(fake.calls) == 2
    # Count a real-looking synthetic hosted row at the full cap; next call must not reach transport.
    rows = list((await db.scalars(select(ModelCall))).all())
    rows[0].cost_usd = 5
    await db.commit()
    with pytest.raises(GatewayError):
        await selected.complete(TaskClass.EXPLAIN_SIMPLE, MESSAGES, learner_id=learner.id)
    assert len(fake.calls) == 2


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "https://u:p@example.com/",
        "https://example.com/?token=private",
        "https://example.com:444/",
    ],
)
async def test_review_rejects_unsafe_urls(client, db, url):
    draft = await accepted(client)
    from app.db.models import CurriculumDraft

    row = await db.get(CurriculumDraft, draft["id"])
    with pytest.raises(AppError):
        await knowledge_reviews.configure(db, row.learner_id, row.id, ReviewPolicyIn(urls=[url]))


async def test_review_invalid_quote_and_owner(client, db, settings, monkeypatch):
    draft = await accepted(client)
    from app.db.models import CurriculumDraft, LearnerProfile

    row = await db.get(CurriculumDraft, draft["id"])
    learner = await db.get(LearnerProfile, row.learner_id)
    await enable(db, learner)
    await knowledge_reviews.configure(
        db, learner.id, row.id, ReviewPolicyIn(urls=["https://docs.python.org/3/"])
    )
    fake = FakeProvider(
        name="openai",
        structured={
            "findings": [
                {
                    "claim": "a",
                    "verdict": "supported",
                    "source_index": 1,
                    "quote": "invented evidence",
                    "explanation": "a",
                }
            ]
        },
    )

    async def snapshot(url, focus):
        return {"url": url, "sha256": "h", "excerpt": "Actual source", "fetched_at": "now"}

    monkeypatch.setattr("app.orchestrator.knowledge_reviews.snapshot", snapshot)
    result = await run(
        db,
        ModelGateway(db, Router("default"), {"openai": fake}, Budget(0)),
        settings,
        learner.id,
        row.id,
    )
    assert result.history_json[-1]["outcome"] == "failed"
    assert result.history_json[-1]["error"] == "review_evidence_invalid"
    other = LearnerProfile(display_name="Other fixture")
    db.add(other)
    await db.commit()
    with pytest.raises(KeyError):
        await knowledge_reviews.get(db, other.id, row.id)


async def test_scoped_openai_transport_uses_fixed_endpoint_and_no_local_metadata(monkeypatch):
    from litellm import ModelResponse

    spec = SPEC.model_copy(update={"price_in_per_mtok": 0.125, "price_out_per_mtok": 0.5})
    call = AsyncMock(
        return_value=ModelResponse(
            choices=[{"message": {"role": "assistant", "content": "Synthetic reply"}}],
            usage={"prompt_tokens": 10, "completion_tokens": 5},
        )
    )
    monkeypatch.setattr("litellm.acompletion", call)
    with authoring_scope(spec.registry_id, MESSAGES):
        reply = await OpenAIProvider("synthetic-not-real").complete(
            spec, MESSAGES, metadata={"authoring_receipt": {"draft_id": "private-local-id"}}
        )
    assert reply.text == "Synthetic reply"
    args = call.call_args.kwargs
    assert args["api_base"] == "https://api.openai.com/v1" and args["store"] is False
    assert "metadata" not in args
    with pytest.raises(SourcePolicyDenied):
        await OpenAIProvider("synthetic-not-real").complete(spec, MESSAGES)
    assert call.await_count == 1


async def test_review_history_export_wipe_and_scheduler(client, db, settings, monkeypatch):
    from app.core.factual_review_jobs import tick
    from app.db.models import CurriculumDraft, LearnerProfile
    from app.db.portability import export_learner, wipe_learner
    from app.db.session import sync_connect

    draft = await accepted(client)
    row = await db.get(CurriculumDraft, draft["id"])
    learner = await db.get(LearnerProfile, row.learner_id)
    policy = await knowledge_reviews.configure(
        db, learner.id, row.id, ReviewPolicyIn(urls=["https://docs.python.org/3/"])
    )
    policy.history_json = [
        {
            "id": "synthetic-run",
            "draft_id": row.id,
            "draft_version": row.version,
            "checked_at": "now",
            "outcome": "sources_unchanged",
        }
    ]
    await db.commit()
    app = client._transport.app
    app.state.budget_lock = asyncio.Lock()
    spy = AsyncMock()
    monkeypatch.setattr("app.core.factual_review_jobs.run", spy)
    await tick(app)
    spy.assert_not_called()
    await enable(db, learner)
    # The file method is synchronous and deliberately exercised on a worker thread.
    from starlette.concurrency import run_in_threadpool

    await run_in_threadpool(settings.save_authoring_key, "synthetic-key-for-worker-fixture")
    await tick(app)
    assert spy.await_count == 1 and spy.call_args.kwargs["manual"] is False

    def portable():
        connection = sync_connect(settings.sync_database_url)
        try:
            exported = export_learner(connection, learner.id)
            wipe_learner(connection, learner.id)
            return exported
        finally:
            connection.close()

    exported = await run_in_threadpool(portable)
    assert exported["knowledge_review"][0]["id"] == policy.id
    assert "synthetic-key-for-worker-fixture" not in str(exported)
    assert not (await db.scalars(select(KnowledgeReview))).all()


async def test_hosted_research_saved_reply_and_accepted_reading_are_reused_locally(client, db):
    from app.db.models import LearnerProfile, SkillNode
    from tests.test_knowledge_authoring import material

    learner = await db.scalar(select(LearnerProfile))
    if learner is None:
        await client.get("/api/learner/me")
        learner = await db.scalar(select(LearnerProfile))
    await enable(db, learner)
    fake = FakeProvider(
        name="openai",
        structured={
            "answer_sentence": "The + operator joins two strings; use str() to explicitly convert a number first.",
            "source_indices": [1],
        },
    )
    client._transport.app.state.providers["openai"] = fake
    body = complete(
        research={
            "passage": material()["notes"],
            "topic": "Python concatenation",
            "questions": [
                {
                    "id": "q",
                    "prompt": "How can a number be joined to text?",
                    "findings": "Use explicit conversion.",
                }
            ],
        }
    )
    draft = (
        await client.post(
            "/api/knowledge-material/drafts", json=body, headers={"Idempotency-Key": str(uuid4())}
        )
    ).json()
    url = f"/api/knowledge-material/drafts/{draft['id']}/research-tutor"
    response = await client.post(
        url, json={"expected_version": draft["version"], "question_id": "q", "action": "discuss"}
    )
    assert response.status_code == 200, response.text
    saved = response.json()
    replay = await client.post(
        url, json={"expected_version": saved["version"], "question_id": "q", "action": "discuss"}
    )
    assert replay.status_code == 200 and replay.json()["reused"]
    assert len(fake.calls) == 1
    history = saved["payload"]["authoring"]["research"]["questions"][0]["tutor_exchanges"]
    assert (
        replay.json()["payload"]["authoring"]["research"]["questions"][0]["tutor_exchanges"]
        == history
    )
    published = await client.post(
        f"/api/curriculum/drafts/{draft['id']}/publish", json={"expected_version": saved["version"]}
    )
    assert published.status_code == 200, published.text
    slug = published.json()["draft"]["payload"]["skills"][0]["slug"]
    skill = await db.scalar(select(SkillNode).where(SkillNode.slug == slug))
    for _ in range(2):
        reading = await client.get(f"/api/knowledge-material/skills/{skill.id}/reading")
        assert reading.status_code == 200 and reading.json()["explanation"] == body["explanation"]
    assert len(fake.calls) == 1
