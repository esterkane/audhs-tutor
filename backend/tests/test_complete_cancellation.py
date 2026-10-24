"""A cancelled structured attempt remains accounted for without retrying."""

import asyncio

import pytest
from sqlalchemy import select

from app.db.models import BudgetReservation, ModelCall
from app.models_ai import registry
from app.models_ai.budget import Budget
from app.models_ai.provider import Message, TaskClass
from tests.test_ask_sources import setup


@pytest.mark.parametrize("hosted", [False, True])
async def test_cancelled_complete_records_attempt_and_propagates(
    db, learner, fake_local, monkeypatch, hosted
):
    gateway, _, _, _ = await setup(db, learner, fake_local)
    if hosted:
        await registry.set_status(db, "hosted-strong", "ready")
        gateway.providers["anthropic"] = fake_local
        gateway.budget = Budget(1)
    attempts = 0

    async def cancelled(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        raise asyncio.CancelledError()

    monkeypatch.setattr(fake_local, "complete", cancelled)
    with pytest.raises(asyncio.CancelledError):
        await gateway.complete(
            TaskClass.GRADE_RUBRIC if hosted else TaskClass.CHAT,
            [Message(role="user", content="Synthetic")],
            learner_id=learner.id,
        )
    assert attempts == 1
    row = (await db.scalars(select(ModelCall))).one()
    assert row.outcome == "cancelled"
    assert not row.ok
    assert row.usage_source == "unavailable"
    assert row.cost_status == ("unknown" if hosted else "free")
    if hosted:
        reservation = (await db.scalars(select(BudgetReservation))).one()
        assert reservation.status == "reconciled"
        assert reservation.settled_usd == reservation.amount_usd > 0
        assert reservation.model_call_id == row.id
    assert row.tokens_in == row.tokens_out == 0
