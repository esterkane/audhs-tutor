"""Suspension must cover existing review queues without erasing scheduling/history."""

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db import models, workspace_requests
from app.kernel import memory, question_state
from app.schemas.question_state import QuestionTransitionIn
from tests.test_review_content_versions import count, prepare


async def suspend(db, item, source, *, mode="suspend", revision=0):
    result = await question_state.transition(
        db,
        item.learner_id,
        source.id,
        QuestionTransitionIn(request_id=uuid4(), action=mode, expected_revision=revision),
    )
    await db.commit()
    return result


async def test_queued_card_excluded_and_stale_rating_rejected(client, db):
    item, source, body, _ = await prepare(client, db, assessment=True)
    before = list((await db.execute(select(models.MemoryState.__table__))).mappings())
    await suspend(db, item, source)
    assert await memory.due_items(db, item.learner_id) == []
    summary = await memory.skill_memory_summary(db, item.learner_id, item.skill_id)
    assert summary["due"] == summary["items"] == 0
    refreshed = await client.get(
        f"/api/review/items/{item.id}", params={"session_id": body["session_id"]}
    )
    assert refreshed.status_code == 404
    response = await client.post(
        f"/api/review/{item.id}", json=body, headers={"Idempotency-Key": str(uuid4())}
    )
    assert response.status_code == 409
    assert await count(db, models.ReviewLog) == 0
    assert await count(db, models.WorkspaceRequest) == 0
    assert list((await db.execute(select(models.MemoryState.__table__))).mappings()) == before


async def test_restore_requires_fresh_view_and_preserves_schedule(client, db):
    item, source, body, _ = await prepare(client, db, assessment=True)
    before = list((await db.execute(select(models.MemoryState.__table__))).mappings())
    await suspend(db, item, source)
    await suspend(db, item, source, mode="restore", revision=1)
    assert len(await memory.due_items(db, item.learner_id)) == 1
    assert list((await db.execute(select(models.MemoryState.__table__))).mappings()) == before
    stale = await client.post(f"/api/review/{item.id}", json=body)
    assert stale.status_code == 409
    shown = await client.get(
        f"/api/review/items/{item.id}", params={"session_id": body["session_id"]}
    )
    assert shown.status_code == 200
    body["content_version"] = shown.json()["content_version"]
    assert (await client.post(f"/api/review/{item.id}", json=body)).status_code == 200


async def test_completed_replay_after_suspension(client, db):
    item, source, body, _ = await prepare(client, db, assessment=True)
    headers = {"Idempotency-Key": str(uuid4())}
    first = await client.post(f"/api/review/{item.id}", json=body, headers=headers)
    assert first.status_code == 200
    await suspend(db, item, source)
    again = await client.post(f"/api/review/{item.id}", json=body, headers=headers)
    assert again.json() == first.json()
    assert await count(db, models.ReviewLog) == 1


async def test_suspension_after_claim_rolls_back_without_evidence(client, db, monkeypatch):
    item, source, body, _ = await prepare(client, db, assessment=True)
    original = workspace_requests.claim

    async def changed(*args, **kwargs):
        result = await original(*args, **kwargs)
        await question_state.transition(
            args[0],
            item.learner_id,
            source.id,
            QuestionTransitionIn(request_id=uuid4(), expected_revision=0, action="suspend"),
        )
        return result

    monkeypatch.setattr(workspace_requests, "claim", changed)
    response = await client.post(
        f"/api/review/{item.id}", json=body, headers={"Idempotency-Key": str(uuid4())}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "review_content_changed_during_rating"
    assert await count(db, models.ReviewLog) == 0
    assert await count(db, models.WorkspaceRequest) == 0


async def test_vocab_reference_and_other_learner_not_suspended(client, db):
    item, source, _, _ = await prepare(client, db, assessment=True)
    vocab, _ = await memory.ensure_item(
        db,
        item.learner_id,
        item.skill_id,
        "vocab",
        {"type": "vocab", "ref": source.id, "q": "word", "a": "meaning"},
    )
    other = models.LearnerProfile(display_name="Another learner")
    db.add(other)
    await db.commit()
    other_card, _ = await memory.ensure_item(db, other.id, item.skill_id, "mcq", {"ref": source.id})
    await suspend(db, item, source)
    assert [r.id for r, _ in await memory.due_items(db, item.learner_id)] == [vocab.id]
    assert [r.id for r, _ in await memory.due_items(db, other.id)] == [other_card.id]


async def test_kernel_review_cannot_bypass_suspension(client, db):
    from app.core.errors import AppError

    item, source, _, _ = await prepare(client, db, assessment=True)
    await suspend(db, item, source)
    with pytest.raises(AppError):
        await memory.review(db, item.learner_id, item.id, 4)
    assert await count(db, models.ReviewLog) == 0


async def test_suspension_preserves_historical_memory_signal(client, db):
    item, source, body, _ = await prepare(client, db, assessment=True)
    assert (await client.post(f"/api/review/{item.id}", json=body)).status_code == 200
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    before = await memory.mean_retrievability(db, item.learner_id, item.skill_id, now=now)
    assert before is not None
    await suspend(db, item, source)
    after = await memory.mean_retrievability(db, item.learner_id, item.skill_id, now=now)
    assert after == before
    assert await count(db, models.ReviewLog) == 1
    summary = await memory.skill_memory_summary(db, item.learner_id, item.skill_id, now=now)
    assert summary["items"] == 0 and summary["mean_retrievability"] == before


async def test_explicit_reference_takes_precedence_and_restore_keeps_disabled_card(client, db):
    item, source, _, _ = await prepare(client, db, assessment=True)
    item.prompt_json = {"assessment_id": source.id, "ref": "unrelated"}
    await db.commit()
    await suspend(db, item, source)
    assert await memory.due_items(db, item.learner_id) == []
    item.active = False
    await db.commit()
    await suspend(db, item, source, mode="restore", revision=1)
    assert await memory.due_items(db, item.learner_id) == []
