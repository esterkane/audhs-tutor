"""Local proposal service: durable replay, attribution, and no learning writes."""

from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.errors import AppError
from app.db.models import AskRequest, ModelCall, TutorAnswer, TutorTrace
from app.orchestrator.ask_context_proposals import suggest
from app.schemas.ask import ConversationBrief
from tests.test_ask_context_inputs import turn
from tests.test_ask_sources import setup


async def test_empty_suggestion_replays_without_sources_or_parent(db, learner, fake_local):
    gateway, body, chunk, _ = await setup(db, learner, fake_local)
    parent = await turn(db, learner)
    await db.commit()
    fake_local.structured = {"changes": []}
    key = str(uuid4())
    result = await suggest(
        db, gateway, learner.id, parent.id, None, ConversationBrief(), body.sources, key
    )
    assert result.proposal.changes == []
    assert result.inputs["S1"].origin == "selected_source"
    message = fake_local.calls[0].messages[-1].content
    assert message.count("</context_data>") == 1
    assert "</retrieved_data>" not in message
    parent_id = parent.id
    await db.delete(parent)
    chunk.text = "Changed source"
    await db.commit()
    replay = await suggest(
        db, gateway, learner.id, parent_id, None, ConversationBrief(), body.sources, key
    )
    assert replay == result
    assert len(fake_local.calls) == 1
    assert await db.scalar(select(func.count()).select_from(TutorAnswer)) == 0
    trace = (await db.scalars(select(TutorTrace))).one()
    assert trace.turn_id == result.proposal_id
    assert trace.model_call_id
    assert await db.scalar(select(func.count()).select_from(ModelCall)) == 1


async def test_invalid_attribution_keeps_pending_and_does_not_repeat(db, learner, fake_local):
    gateway, _, _, _ = await setup(db, learner, fake_local)
    parent = await turn(db, learner)
    await db.commit()
    learner_id, parent_id = learner.id, parent.id
    fake_local.structured = {
        "changes": [
            {
                "field": "notes",
                "value": "Unsupported",
                "rationale": "Keep this",
                "input_ids": ["invented"],
            }
        ]
    }
    key = str(uuid4())
    with pytest.raises(AppError, match="could not be matched"):
        await suggest(db, gateway, learner_id, parent_id, None, ConversationBrief(), None, key)
    with pytest.raises(AppError, match="still running or was interrupted"):
        await suggest(db, gateway, learner_id, parent_id, None, ConversationBrief(), None, key)
    assert len(fake_local.calls) == 1
    claim = (await db.scalars(select(AskRequest))).one()
    assert claim.response_json is None
    assert await db.scalar(select(func.count()).select_from(TutorTrace)) == 0
    assert await db.scalar(select(func.count()).select_from(ModelCall)) == 1


async def test_trace_failure_rolls_back_receipt_but_keeps_call(
    db, learner, fake_local, monkeypatch
):
    from app.orchestrator import ask_context_proposals as service

    gateway, _, _, _ = await setup(db, learner, fake_local)
    parent = await turn(db, learner)
    await db.commit()
    learner_id, parent_id = learner.id, parent.id
    fake_local.structured = {"changes": []}
    key = str(uuid4())

    async def fail(*args, **kwargs):
        raise RuntimeError("simulated trace failure")

    monkeypatch.setattr(service, "write_tutor_trace", fail)
    with pytest.raises(RuntimeError, match="simulated"):
        await suggest(db, gateway, learner_id, parent_id, None, ConversationBrief(), None, key)
    with pytest.raises(AppError, match="still running or was interrupted"):
        await suggest(db, gateway, learner_id, parent_id, None, ConversationBrief(), None, key)
    assert len(fake_local.calls) == 1
    assert (await db.scalars(select(AskRequest))).one().response_json is None
    assert await db.scalar(select(func.count()).select_from(ModelCall)) == 1


async def test_transport_denial_sends_nothing(db, learner, fake_local, monkeypatch):
    from app.models_ai.gateway import GatewayError
    from app.models_ai.source_policy import SourcePolicyDenied

    gateway, _, _, _ = await setup(db, learner, fake_local)
    parent = await turn(db, learner)
    await db.commit()

    async def denied(spec):
        raise SourcePolicyDenied("unverified transport")

    monkeypatch.setattr(fake_local, "validate_local_transport", denied)
    with pytest.raises(GatewayError):
        await suggest(
            db, gateway, learner.id, parent.id, None, ConversationBrief(), None, str(uuid4())
        )
    assert not fake_local.calls
    assert (await db.scalars(select(AskRequest))).one().response_json is None


async def test_duplicate_request_during_generation_does_not_dispatch(
    db, learner, fake_local, session_factory, monkeypatch
):
    import asyncio

    from app.models_ai.budget import Budget
    from app.models_ai.gateway import ModelGateway
    from app.models_ai.routing import Router

    _, _, _, _ = await setup(db, learner, fake_local)
    parent = await turn(db, learner)
    await db.commit()
    learner_id, parent_id = learner.id, parent.id
    key = str(uuid4())
    fake_local.structured = {"changes": []}
    entered, release = asyncio.Event(), asyncio.Event()
    original = fake_local.complete

    async def delayed(*args, **kwargs):
        entered.set()
        await release.wait()
        return await original(*args, **kwargs)

    monkeypatch.setattr(fake_local, "complete", delayed)

    async def request():
        async with session_factory() as session:
            gateway = ModelGateway(session, Router("default"), {"ollama": fake_local}, Budget(0))
            return await suggest(
                session, gateway, learner_id, parent_id, None, ConversationBrief(), None, key
            )

    first = asyncio.create_task(request())
    try:
        await asyncio.wait_for(entered.wait(), timeout=5)
        with pytest.raises(AppError, match="still running or was interrupted"):
            await request()
    finally:
        release.set()
        result = await asyncio.wait_for(first, timeout=5)
    assert (await request()) == result
    assert len(fake_local.calls) == 1


async def test_unchanged_value_is_not_offered_as_a_change(db, learner, fake_local):
    gateway, _, _, _ = await setup(db, learner, fake_local)
    parent = await turn(db, learner)
    await db.commit()
    fake_local.structured = {
        "changes": [
            {
                "field": "notes",
                "value": "",
                "rationale": "No notes exist",
                "input_ids": ["T1:question"],
            }
        ]
    }
    result = await suggest(
        db, gateway, learner.id, parent.id, None, ConversationBrief(), None, str(uuid4())
    )
    assert result.proposal.changes == []
