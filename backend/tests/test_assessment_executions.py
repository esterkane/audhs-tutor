"""Execution staging stays separate from claims and atomic learning completion."""

from types import SimpleNamespace

import pytest
from sqlalchemy import delete, select

from app.core.errors import AppError
from app.db import assessment_executions as executions
from app.db import workspace_requests
from app.db.models import AssessmentExecution, Session, WorkspaceRequest


async def new_claim(db, learner, key="assessment:one"):
    session = Session(learner_id=learner.id, mode="steady", energy=3, socratic=False)
    db.add(session)
    await db.commit()
    claim = WorkspaceRequest(
        learner_id=learner.id,
        session_id=session.id,
        request_key=key,
        fingerprint="fingerprint",
        response_json=None,
    )
    db.add(claim)
    await db.commit()
    return claim.id


async def prepare(db, learner, claim_id):
    await executions.prepare(
        db,
        learner.id,
        claim_id,
        request_json={"answer": "private learner answer"},
        content_fingerprint="stable-hash",
    )


@pytest.mark.asyncio
async def test_staging_completion_rolls_back_with_outcome(db, learner):
    learner = SimpleNamespace(id=learner.id)
    claim_id = await new_claim(db, learner)
    await prepare(db, learner, claim_id)
    await executions.mark_inference_started(db, learner.id, claim_id)
    with pytest.raises(AppError):
        await executions.mark_inference_started(db, learner.id, claim_id)
    await executions.save_grade(db, learner.id, claim_id, grade_json={"score": 1})
    await workspace_requests.complete(db, learner.id, claim_id, {"done": True}, commit=False)
    await executions.mark_completed(db, learner.id, claim_id)
    await db.rollback()
    row = await executions.get_owned(db, learner.id, claim_id)
    assert row.phase == "grade_ready"
    claim = await db.get(WorkspaceRequest, claim_id)
    assert claim.response_json is None
    await workspace_requests.complete(db, learner.id, claim_id, {"done": True}, commit=False)
    await executions.mark_completed(db, learner.id, claim_id)
    await db.commit()
    assert (await executions.get_owned(db, learner.id, claim_id)).phase == "completed"


@pytest.mark.asyncio
async def test_legacy_missing_and_foreign_claim_never_inferred(db, learner):
    learner = SimpleNamespace(id=learner.id)
    claim_id = await new_claim(db, learner)
    assert await executions.get_owned(db, learner.id, claim_id) is None
    with pytest.raises(AppError):
        await executions.mark_inference_started(db, learner.id, claim_id)
    with pytest.raises(AppError):
        await executions.prepare(
            db, "other-owner", claim_id, request_json={"answer": "x"}, content_fingerprint="hash"
        )
    assert await executions.get_owned(db, learner.id, claim_id) is None
    with pytest.raises(AppError):
        await executions.save_grade(db, learner.id, claim_id, grade_json={"score": 1})


@pytest.mark.asyncio
async def test_result_immutable_and_claim_cascade(db, learner):
    learner = SimpleNamespace(id=learner.id)
    claim_id = await new_claim(db, learner)
    await prepare(db, learner, claim_id)
    # Deterministic graders may stage directly without inference.
    await executions.save_grade(db, learner.id, claim_id, grade_json={"score": 1})
    await executions.save_grade(db, learner.id, claim_id, grade_json={"score": 1})
    with pytest.raises(AppError):
        await executions.save_grade(db, learner.id, claim_id, grade_json={"score": 0})
    assert (await executions.get_owned(db, learner.id, claim_id)).grade_json == {"score": 1}
    await db.execute(delete(WorkspaceRequest).where(WorkspaceRequest.id == claim_id))
    await db.commit()
    assert await db.scalar(select(AssessmentExecution)) is None


@pytest.mark.asyncio
async def test_reject_nonassessment_and_duplicate_prepare(db, learner):
    learner = SimpleNamespace(id=learner.id)
    review_id = await new_claim(db, learner, "review:one")
    with pytest.raises(AppError):
        await prepare(db, learner, review_id)
    claim_id = await new_claim(db, learner)
    await prepare(db, learner, claim_id)
    with pytest.raises(AppError):
        await prepare(db, learner, claim_id)
    with pytest.raises(AppError):
        await executions.mark_completed(db, learner.id, claim_id)
    await db.rollback()


def test_migration_does_not_infer_legacy_execution(tmp_path):
    import sqlite3

    from alembic import command
    from app.db.migrate import alembic_config

    path = tmp_path / "migration.db"
    cfg = alembic_config(f"sqlite:///{path}")
    command.upgrade(cfg, "a42e7f90d821")
    with sqlite3.connect(path) as conn:
        conn.execute(
            "INSERT INTO learner_profile (id, display_name, settings_json, created_at) "
            "VALUES ('l', 'test', '{}', 'now')"
        )
        conn.execute(
            "INSERT INTO session (id, learner_id, started_at, mode, energy, socratic, planned_blocks_json) "
            "VALUES ('s', 'l', 'now', 'steady', 3, 0, '[]')"
        )
        conn.execute(
            "INSERT INTO workspace_request (id, learner_id, session_id, request_key, fingerprint, created_at) "
            "VALUES ('c', 'l', 's', 'assessment:legacy', 'hash', 'now')"
        )
    command.upgrade(cfg, "head")
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT count(*) FROM assessment_execution").fetchone()[0] == 0
        assert (
            conn.execute("SELECT response_json FROM workspace_request WHERE id='c'").fetchone()[0]
            is None
        )
    command.downgrade(cfg, "a42e7f90d821")
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT count(*) FROM workspace_request").fetchone()[0] == 1
