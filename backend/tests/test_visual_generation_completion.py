import asyncio
import json

import pytest
from sqlalchemy import func, select

from app.core.errors import AppError
from app.db.models import AuthoredVisualDocument as Document
from app.db.models import AuthoredVisualVersion as Version
from app.db.models import LearnerProfile, ModelCall, TutorAnswer
from app.db.models import VisualGenerationRequest as Generation
from app.kernel.authored_visuals import VisualRepository, digest
from app.kernel.visual_generation import GenerationRequests
from app.schemas.authored_visuals import AnswerRelationshipVisual
from tests.test_authored_visual_commands import ask_spec


async def prepared(db, learner, factory):
    spec = AnswerRelationshipVisual.model_validate_json(json.dumps(await ask_spec(db, learner)))
    repo = GenerationRequests(factory)
    row = await repo.reserve(learner.id, "generate", spec.binding, "visual.v1")
    token = await repo.claim(learner.id, row.id)
    assert await repo.take_attempt(learner.id, row.id, token)
    call = ModelCall(
        learner_id=learner.id,
        provider="ollama",
        model="synthetic",
        registry_id="local-test",
        task="format",
        metadata_json={
            "surface": "ask_visual",
            "generation_id": row.id,
            "binding_sha256": digest(row.binding_json),
            "prompt_version": "visual.v1",
        },
    )
    db.add(call)
    await db.commit()
    return repo, row, token, spec, call


async def test_complete_once_and_cancel_cannot_erase_result(db, learner, session_factory):
    repo, row, token, spec, call = await prepared(db, learner, session_factory)
    results = await asyncio.gather(
        *[repo.complete(learner.id, row.id, token, spec, call.id) for _ in range(2)]
    )
    assert len(set(results)) == 1
    cancelled = await repo.cancel(learner.id, row.id)
    assert cancelled.state == "completed"
    async with session_factory() as check:
        assert await check.scalar(select(func.count()).select_from(Version)) == 1
        version = await check.get(Version, results[0])
        assert version.origin_json["model"] == "local-test"
        assert version.origin_json["prompt_version"] == "visual.v1"


@pytest.mark.parametrize(
    "failure", ["cancel", "restart", "answer", "call", "token", "hosted", "foreign"]
)
async def test_stale_or_mismatched_work_cannot_publish(db, learner, session_factory, failure):
    repo, row, token, spec, call = await prepared(db, learner, session_factory)
    if failure == "cancel":
        await repo.cancel(learner.id, row.id)
    elif failure == "restart":
        await repo.interrupt_abandoned()
    elif failure == "answer":
        (await db.get(TutorAnswer, "root")).text = "Changed"
        await db.commit()
    elif failure == "call":
        call.metadata_json = {}
        await db.commit()
    elif failure == "hosted":
        call.provider = "openai"
        await db.commit()
    elif failure == "foreign":
        other = LearnerProfile(display_name="Other")
        db.add(other)
        await db.flush()
        call.learner_id = other.id
        await db.commit()
    else:
        token = "stale"
    with pytest.raises(AppError):
        await repo.complete(learner.id, row.id, token, spec, call.id)
    async with session_factory() as check:
        assert await check.scalar(select(func.count()).select_from(Document)) == 0
        assert (await check.get(Generation, row.id)).result_version_id is None


async def test_version_flush_failure_rolls_back_result_together(
    db, learner, session_factory, monkeypatch
):
    repo, row, token, spec, call = await prepared(db, learner, session_factory)
    original = VisualRepository._save

    async def interrupted(*args, **kwargs):
        await original(*args, **kwargs)
        raise asyncio.CancelledError()

    monkeypatch.setattr(VisualRepository, "_save", interrupted)
    with pytest.raises(asyncio.CancelledError):
        await repo.complete(learner.id, row.id, token, spec, call.id)
    async with session_factory() as check:
        assert await check.scalar(select(func.count()).select_from(Document)) == 0
        assert (await check.get(Generation, row.id)).state == "running"


async def test_cancellation_racing_save_has_one_consistent_outcome(db, learner, session_factory):
    repo, row, token, spec, call = await prepared(db, learner, session_factory)
    await asyncio.gather(
        repo.complete(learner.id, row.id, token, spec, call.id),
        repo.cancel(learner.id, row.id),
        return_exceptions=True,
    )
    async with session_factory() as check:
        request = await check.get(Generation, row.id)
        count = await check.scalar(select(func.count()).select_from(Version))
        assert (request.state, count) in {("completed", 1), ("cancelled", 0)}
        assert bool(request.result_version_id) == (request.state == "completed")
