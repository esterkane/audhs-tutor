"""Eligibility foundation: learner isolation, retries, atomicity and retained history."""

import asyncio
import sqlite3
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.errors import AppError
from app.db import models
from app.db.portability import export_learner, wipe_learner
from app.kernel import question_state as qs
from app.schemas.question_state import QuestionTransitionIn


async def item(db):
    skill = models.SkillNode(slug=str(uuid4()), title="Synthetic skill", domain="ai_ml")
    db.add(skill)
    await db.flush()
    question = models.Assessment(skill_id=skill.id, kind="mcq", item_json={"question": "Why?"})
    db.add(question)
    await db.commit()
    return question


def action(revision=0, mode="suspend", request_id=None):
    return QuestionTransitionIn(
        request_id=request_id or uuid4(),
        expected_revision=revision,
        action=mode,
        reason="Needs correction",
    )


async def test_isolation_replay_restore_and_history(db, learner):
    q = await item(db)
    other = models.LearnerProfile(display_name="Other")
    db.add(other)
    card = models.ReviewItem(
        learner_id=learner.id,
        skill_id=q.skill_id,
        item_type="mcq",
        prompt_json={"ref": q.id},
        active=False,
    )
    attempt = models.AssessmentAttempt(
        learner_id=learner.id, assessment_id=q.id, answer="Old answer"
    )
    db.add_all([card, attempt])
    await db.commit()
    request = action()
    first = await qs.transition(db, learner.id, q.id, request)
    await db.commit()
    assert first.state == "suspended" and first.revision == 1
    assert (await qs.read(db, other.id, q.id)).state == "active"
    assert (await db.scalars(select(models.Assessment).where(qs.eligible(learner.id)))).all() == []
    assert (
        len((await db.scalars(select(models.Assessment).where(qs.eligible(other.id)))).all()) == 1
    )
    restored = await qs.transition(db, learner.id, q.id, action(1, "restore"))
    await db.commit()
    assert restored.state == "active" and restored.revision == 2
    assert await qs.transition(db, learner.id, q.id, request) == first
    await db.commit()
    assert (await qs.read(db, learner.id, q.id)).revision == 2  # replay did not undo restore
    await db.refresh(card)
    assert not card.active  # restore never revives an independently disabled review
    assert await db.get(models.AssessmentAttempt, attempt.id) is not None
    assert await db.scalar(select(func.count()).select_from(models.QuestionTransition)) == 2
    assert await db.scalar(select(func.count()).select_from(models.LearningEvent)) == 0
    assert await db.scalar(select(func.count()).select_from(models.CompetencyEvidence)) == 0


async def test_conflicts_missing_and_rollback(db, learner):
    q = await item(db)
    lid, qid = learner.id, q.id
    req = action()
    await qs.transition(db, lid, qid, req)
    await db.rollback()
    assert (await qs.read(db, lid, qid)).revision == 0
    assert await db.scalar(select(func.count()).select_from(models.QuestionTransition)) == 0
    await qs.transition(db, lid, qid, req)
    await db.commit()
    for body, code in [
        (action(), "question_state_conflict"),
        (action(1), "question_transition_invalid"),
        (action(1, "restore", req.request_id), "question_request_conflict"),
    ]:
        with pytest.raises(AppError) as err:
            await qs.transition(db, lid, qid, body)
        assert err.value.code == code
        await db.rollback()
    with pytest.raises(AppError) as err:
        await qs.transition(db, lid, "missing", action())
    assert err.value.http_status == 404
    await db.rollback()


@pytest.mark.parametrize("state", ["superseded", "retired"])
async def test_restore_cannot_revive_terminal_states(db, learner, state):
    q = await item(db)
    db.add(
        models.QuestionState(
            learner_id=learner.id,
            assessment_id=q.id,
            state=state,
            revision=1,
            reason="Old",
            updated_at="2026-10-08",
        )
    )
    await db.commit()
    with pytest.raises(AppError) as err:
        await qs.transition(db, learner.id, q.id, action(1, "restore"))
    assert err.value.code == "question_transition_invalid"


async def test_concurrent_revision_one_winner(db, learner, session_factory):
    q = await item(db)
    lid, qid = learner.id, q.id

    async def run(body):
        async with session_factory() as s:
            try:
                result = await qs.transition(s, lid, qid, body)
                await s.commit()
                return result.state
            except AppError as exc:
                await s.rollback()
                return exc.code

    assert sorted(await asyncio.gather(run(action()), run(action()))) == [
        "question_state_conflict",
        "suspended",
    ]


async def test_export_wipe_scope(db, learner, db_path):
    q = await item(db)
    other = models.LearnerProfile(display_name="Other")
    db.add(other)
    await db.commit()
    await qs.transition(db, learner.id, q.id, action())
    await qs.transition(db, other.id, q.id, action())
    await db.commit()
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        exported = export_learner(conn, learner.id)
        assert exported["question_state"][0]["state"] == "suspended"
        assert len(exported["question_transition"]) == 1
        deleted = wipe_learner(conn, learner.id)
        assert deleted["question_state"] == deleted["question_transition"] == 1
        assert len(export_learner(conn, other.id)["question_state"]) == 1
        assert len(export_learner(conn, other.id)["question_transition"]) == 1


async def test_concurrent_same_identity_replays_once(db, learner, session_factory):
    q = await item(db)
    lid, qid, request = learner.id, q.id, action()

    async def run():
        async with session_factory() as s:
            result = await qs.transition(s, lid, qid, request)
            await s.commit()
            return result

    first, second = await asyncio.gather(run(), run())
    assert first == second and first.revision == 1
    assert await db.scalar(select(func.count()).select_from(models.QuestionTransition)) == 1


async def test_request_identity_cannot_target_another_question(db, learner):
    first, second = await item(db), await item(db)
    request = action()
    await qs.transition(db, learner.id, first.id, request)
    await db.commit()
    with pytest.raises(AppError) as err:
        await qs.transition(db, learner.id, second.id, request)
    assert err.value.code == "question_request_conflict"
    assert (await qs.read(db, learner.id, second.id)).revision == 0
