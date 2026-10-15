"""Proposal receipts stay owned, immutable and separate from learning evidence."""

from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.errors import AppError
from app.db import ask_requests
from app.db.models import AskRequest, TutorAnswer
from app.orchestrator import ask_context_receipts as receipts
from app.orchestrator.answer_check_binding import text_hash
from app.orchestrator.ask_context_inputs import resolve
from app.schemas.ask import ConversationBrief
from app.schemas.ask_context_proposals import ContextProposal
from tests.test_ask_context_inputs import turn


async def setup(db, learner):
    row = await turn(db, learner, text="UNREFERENCED_PRIVATE_SOURCE_TEXT")
    brief = ConversationBrief(task="Current task")
    await db.commit()
    inputs = await resolve(db, learner.id, row.id, None, brief)
    payload = receipts.request_payload(row.id, None, brief, None)
    key = str(uuid4())
    identity, _ = await ask_requests.claim(db, learner.id, key, payload)
    text = inputs.inputs["T1:question"].text
    proposal = ContextProposal.model_validate(
        {
            "changes": [
                {
                    "field": "notes",
                    "value": "Remember the example",
                    "rationale": "Continue the task",
                    "references": [
                        {
                            "input_id": "T1:question",
                            "text_hash": text_hash(text),
                            "start": 0,
                            "end": len(text),
                        }
                    ],
                }
            ]
        }
    )
    return row, inputs, payload, key, identity, proposal


async def test_receipt_replay_survives_parent_deletion_and_omits_raw_text(db, learner):
    row, inputs, payload, key, identity, proposal = await setup(db, learner)
    result = await receipts.complete(db, learner.id, identity, payload, inputs, proposal)
    await db.commit()
    assert result.inputs["T1:answer"].origin == "unverified_tutor_reply"
    assert "UNREFERENCED_PRIVATE_SOURCE_TEXT" not in result.model_dump_json()
    await db.delete(row)
    await db.commit()
    replay = await receipts.replay(db, learner.id, key, payload)
    assert replay == result
    assert await db.scalar(select(func.count()).select_from(TutorAnswer)) == 0
    assert await receipts.owned(db, learner.id, identity) == result
    with pytest.raises(AppError):
        await receipts.owned(db, "other-owner", identity)


async def test_completion_cannot_overwrite_or_cross_operation(db, learner):
    _, inputs, payload, key, identity, proposal = await setup(db, learner)
    first = await receipts.complete(db, learner.id, identity, payload, inputs, proposal)
    await db.commit()
    proposal.changes[0].value = "Replacement"
    with pytest.raises(AppError):
        await receipts.complete(db, learner.id, identity, payload, inputs, proposal)
    assert await receipts.owned(db, learner.id, identity) == first
    with pytest.raises(ValueError):
        await receipts.replay(
            db, learner.id, key, {**payload, "operation": "context_acceptance.v1"}
        )


async def test_changed_base_and_foreign_completion_rejected(db, learner):
    _, inputs, payload, _, identity, proposal = await setup(db, learner)
    with pytest.raises(AppError):
        await receipts.complete(db, "other-owner", identity, payload, inputs, proposal)
    with pytest.raises(AppError):
        await receipts.complete(
            db,
            learner.id,
            identity,
            {**payload, "brief": ConversationBrief(task="Edited").model_dump()},
            inputs,
            proposal,
        )
    row = await db.get(AskRequest, identity)
    assert row.response_json is None


async def test_wrong_response_envelope_is_not_a_proposal(db, learner):
    _, _, payload, key, identity, _ = await setup(db, learner)
    await ask_requests.complete(db, learner.id, identity, {"operation": "context_acceptance.v1"})
    await db.commit()
    with pytest.raises(ValueError):
        await receipts.replay(db, learner.id, key, payload)


async def test_rollback_leaves_claim_pending(db, learner):
    _, inputs, payload, key, identity, proposal = await setup(db, learner)
    learner_id = learner.id
    await receipts.complete(db, learner_id, identity, payload, inputs, proposal)
    await db.rollback()
    with pytest.raises(AppError, match="still running or was interrupted"):
        await receipts.replay(db, learner_id, key, payload)
    await receipts.complete(db, learner_id, identity, payload, inputs, proposal)
    await db.commit()
    assert (await receipts.owned(db, learner_id, identity)).proposal == proposal


async def test_unrequested_source_is_rejected(db, learner):
    from app.orchestrator.ask_context_binding import ContextInput

    _, inputs, payload, _, identity, proposal = await setup(db, learner)
    inputs.inputs["S1"] = ContextInput("Extra text", "selected_source", "chunk", "a" * 64)
    with pytest.raises(AppError, match="sources do not match"):
        await receipts.complete(db, learner.id, identity, payload, inputs, proposal)


async def test_concurrent_completion_has_one_winner(db, learner, session_factory):
    import asyncio

    _, inputs, payload, _, identity, proposal = await setup(db, learner)
    learner_id = learner.id

    async def finish(value):
        candidate = proposal.model_copy(deep=True)
        candidate.changes[0].value = value
        async with session_factory() as session:
            try:
                result = await receipts.complete(
                    session, learner_id, identity, payload, inputs, candidate
                )
                await session.commit()
                return result
            except AppError as error:
                await session.rollback()
                return error

    results = await asyncio.gather(finish("First"), finish("Second"))
    winners = [result for result in results if not isinstance(result, AppError)]
    assert len(winners) == 1
    errors = [result for result in results if isinstance(result, AppError)]
    assert len(errors) == 1
    assert await receipts.owned(db, learner_id, identity) == winners[0]
