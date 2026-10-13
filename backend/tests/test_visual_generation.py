import asyncio

import pytest
from sqlalchemy import func, select

from app.core.errors import AppError
from app.db.models import LearnerProfile, LearningEvent, ModelCall
from app.db.models import VisualGenerationRequest as Generation
from app.kernel.visual_generation import GenerationRequests
from app.schemas.answer_visual_binding import AnswerVisualBinding
from tests.test_authored_visual_commands import ask_spec


async def reserve(db, learner, factory, **kwargs):
    spec = await ask_spec(db, learner)
    repo = GenerationRequests(factory)
    binding = AnswerVisualBinding.model_validate(spec["binding"])
    row = await repo.reserve(learner.id, "key", binding, "visual.v1", **kwargs)
    return repo, binding, row


async def test_concurrent_reservation_and_single_claim(db, learner, session_factory):
    repo, binding, row = await reserve(db, learner, session_factory)
    results = await asyncio.gather(
        *[repo.reserve(learner.id, "key", binding, "visual.v1") for _ in range(2)]
    )
    assert {r.id for r in results} == {row.id}
    tokens = await asyncio.gather(*[repo.claim(learner.id, row.id) for _ in range(2)])
    assert sum(t is not None for t in tokens) == 1
    with pytest.raises(AppError) as exc:
        await repo.reserve(learner.id, "key", binding, "changed-prompt")
    assert exc.value.http_status == 409
    assert await db.scalar(select(func.count()).select_from(Generation)) == 1
    assert await db.scalar(select(func.count()).select_from(ModelCall)) == 0
    assert await db.scalar(select(func.count()).select_from(LearningEvent)) == 0


async def test_total_attempt_budget_and_terminal_replay(db, learner, session_factory):
    repo, binding, row = await reserve(db, learner, session_factory, attempt_limit=2)
    token = await repo.claim(learner.id, row.id)
    assert not await repo.take_attempt(learner.id, row.id, "stale-worker")
    assert await repo.take_attempt(learner.id, row.id, token)
    assert await repo.take_attempt(learner.id, row.id, token)
    assert not await repo.take_attempt(learner.id, row.id, token)
    replay = await repo.reserve(learner.id, "key", binding, "visual.v1", attempt_limit=2)
    assert (replay.state, replay.attempts, replay.error_code) == ("failed", 2, "attempt_limit")
    assert await repo.claim(learner.id, row.id) is None


@pytest.mark.parametrize("claimed", [False, True])
async def test_cancel_fences_worker_and_does_not_restart(db, learner, session_factory, claimed):
    repo, binding, row = await reserve(db, learner, session_factory)
    token = await repo.claim(learner.id, row.id) if claimed else "not-started"
    assert (await repo.cancel(learner.id, row.id)).state == "cancelled"
    assert not await repo.take_attempt(learner.id, row.id, token)
    assert not await repo.fail(learner.id, row.id, token)
    assert (await repo.reserve(learner.id, "key", binding, "visual.v1")).state == "cancelled"
    assert await repo.claim(learner.id, row.id) is None


async def test_restart_interrupts_without_reclaim_and_owner_isolation(db, learner, session_factory):
    repo, binding, row = await reserve(db, learner, session_factory)
    token = await repo.claim(learner.id, row.id)
    assert await repo.interrupt_abandoned() == 1
    assert await repo.interrupt_abandoned() == 0
    assert not await repo.take_attempt(learner.id, row.id, token)
    assert (await repo.reserve(learner.id, "key", binding, "visual.v1")).state == "interrupted"
    other = LearnerProfile(display_name="Other")
    db.add(other)
    await db.commit()
    with pytest.raises(AppError) as exc:
        await repo.cancel(other.id, row.id)
    assert exc.value.http_status == 404


async def test_pending_caller_edits_untouched_and_cancel_rolls_back(db, learner, session_factory):
    repo, _, row = await reserve(db, learner, session_factory)
    learner.display_name = "Unsaved"
    with pytest.raises(asyncio.CancelledError):
        async with repo.transaction() as tx:
            stored = await tx.get(Generation, row.id)
            stored.state = "cancelled"
            await tx.flush()
            raise asyncio.CancelledError()
    async with session_factory() as check:
        assert (await check.get(Generation, row.id)).state == "pending"
        assert (await check.get(LearnerProfile, learner.id)).display_name == "Test Learner"
    assert learner.display_name == "Unsaved"
