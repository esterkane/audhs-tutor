"""Durable private scratch drafts; repeat safety is independent of learning history."""

import asyncio
import sqlite3
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.errors import AppError
from app.db import models
from app.db.portability import export_learner, wipe_learner
from app.kernel import correction_drafts as drafts
from app.schemas.correction_drafts import (
    CreateCorrectionDraft,
    DiscardCorrectionDraft,
    SaveCorrectionDraft,
)
from tests.test_question_state import item


def create_body(q):
    return CreateCorrectionDraft(
        request_id=uuid4(), assessment_id=q.id, expected_question_revision=0
    )


def save_body(revision=1):
    return SaveCorrectionDraft(
        request_id=uuid4(),
        expected_revision=revision,
        candidate={"item": {"question": "Proposed question"}, "rubric": None},
        rationale="Needs context",
    )


async def test_create_save_discard_replay_preserves_original(db, learner):
    q = await item(db)
    create = create_body(q)
    first = await drafts.create(db, learner.id, create)
    await db.commit()
    before = await drafts.get(db, learner.id, first.draft_id)
    original, identity = before.original_json.copy(), before.original_fingerprint
    save = save_body()
    saved = await drafts.change(db, learner.id, first.draft_id, save)
    await db.commit()
    assert saved.revision == 2
    assert await drafts.create(db, learner.id, create) == first
    assert await drafts.change(db, learner.id, first.draft_id, save) == saved
    discarded = await drafts.change(
        db,
        learner.id,
        first.draft_id,
        DiscardCorrectionDraft(request_id=uuid4(), expected_revision=2),
    )
    await db.commit()
    assert discarded.revision == 3 and discarded.status == "discarded"
    assert await drafts.change(db, learner.id, first.draft_id, save) == saved
    row = await drafts.get(db, learner.id, first.draft_id)
    assert row.status == "discarded" and row.original_json == original
    assert row.original_fingerprint == identity
    assert row.candidate_json == save.candidate
    await db.refresh(q)
    assert q.item_json == original["item"]
    assert await db.scalar(select(func.count()).select_from(models.Assessment)) == 1
    for model in [
        models.AssessmentAttempt,
        models.CompetencyEvidence,
        models.QuestionState,
        models.LearningEvent,
    ]:
        assert await db.scalar(select(func.count()).select_from(model)) == 0


async def test_revision_request_conflicts_and_rollback(db, learner):
    q = await item(db)
    lid = learner.id
    body = create_body(q)
    first = await drafts.create(db, lid, body)
    await db.rollback()
    assert await db.scalar(select(func.count()).select_from(models.QuestionCorrectionDraft)) == 0
    assert await db.scalar(select(func.count()).select_from(models.QuestionCorrectionCommand)) == 0
    first = await drafts.create(db, lid, body)
    await db.commit()
    save = save_body()
    await drafts.change(db, lid, first.draft_id, save)
    await db.commit()
    for request, code in [
        (save_body(), "correction_draft_conflict"),
        (save.model_copy(update={"rationale": "Different body"}), "correction_request_conflict"),
    ]:
        with pytest.raises(AppError) as error:
            await drafts.change(db, lid, first.draft_id, request)
        assert error.value.code == code
        await db.rollback()
    await drafts.change(db, lid, first.draft_id, save_body(2))
    await db.rollback()
    assert (await drafts.get(db, lid, first.draft_id)).revision == 2
    assert await db.scalar(select(func.count()).select_from(models.QuestionCorrectionCommand)) == 2


async def test_concurrent_creates_and_saves(db, learner, session_factory):
    q = await item(db)
    lid, body = learner.id, create_body(q)

    async def create():
        async with session_factory() as session:
            result = await drafts.create(session, lid, body)
            await session.commit()
            return result

    first, same = await asyncio.gather(create(), create())
    assert first == same

    async def save():
        async with session_factory() as session:
            try:
                await drafts.change(session, lid, first.draft_id, save_body())
                await session.commit()
                return "saved"
            except AppError as error:
                await session.rollback()
                return error.code

    assert sorted(await asyncio.gather(save(), save())) == ["correction_draft_conflict", "saved"]
    assert await db.scalar(select(func.count()).select_from(models.QuestionCorrectionDraft)) == 1


async def test_export_wipe_and_foreign_draft_access(db, learner, db_path):
    q = await item(db)
    other = models.LearnerProfile(display_name="Other")
    db.add(other)
    await db.commit()
    lid, oid = learner.id, other.id
    first = await drafts.create(db, lid, create_body(q))
    second = await drafts.create(db, oid, create_body(q))
    await db.commit()
    with pytest.raises(AppError) as error:
        await drafts.get(db, oid, first.draft_id)
    assert error.value.http_status == 404
    with pytest.raises(AppError):
        await drafts.change(db, oid, first.draft_id, save_body())
    await db.rollback()
    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        exported = export_learner(connection, lid)
        assert len(exported["question_correction_draft"]) == 1
        assert len(exported["question_correction_command"]) == 1
        wiped = wipe_learner(connection, lid)
        assert wiped["question_correction_draft"] == wiped["question_correction_command"] == 1
        assert (
            export_learner(connection, oid)["question_correction_draft"][0]["id"] == second.draft_id
        )
        assert connection.execute("SELECT count(*) FROM assessment").fetchone()[0] == 1


async def test_report_ownership_and_changed_report_conflict(db, learner):
    q = await item(db)
    original = await drafts.original(db, q.id)
    report = models.QuestionFeedback(
        learner_id=learner.id,
        assessment_id=q.id,
        target_key="test",
        verdict="bad",
        labels_json=["incorrect"],
        snapshot_json={
            "kind": original["kind"],
            "item": original["item"],
            "skill_id": original["skill_id"],
        },
    )
    db.add(report)
    await db.commit()
    lid = learner.id
    body = create_body(q).model_copy(update={"feedback_id": report.id})
    await drafts.create(db, lid, body)
    await db.commit()
    q.item_json = {"question": "Changed question"}
    await db.commit()
    with pytest.raises(AppError) as error:
        await drafts.create(db, lid, body.model_copy(update={"request_id": uuid4()}))
    assert error.value.code == "correction_report_conflict"
    await db.rollback()


def test_candidate_limits_and_stable_identity():
    assert drafts.fingerprint({"a": 1, "b": 2}) == drafts.fingerprint({"b": 2, "a": 1})
    assert drafts.fingerprint({"a": 1}) != drafts.fingerprint({"a": 2})
    with pytest.raises(ValueError):
        SaveCorrectionDraft(
            request_id=uuid4(), expected_revision=1, candidate={"large": "x" * 100001}
        )
    with pytest.raises(ValueError):
        SaveCorrectionDraft(
            request_id=uuid4(), expected_revision=1, candidate={"invalid": float("nan")}
        )
