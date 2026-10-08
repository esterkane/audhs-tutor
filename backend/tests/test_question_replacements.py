"""Lineage cannot redirect history or cross a learner/content boundary."""

import sqlite3

import pytest
from sqlalchemy import func, select

from app.core.errors import AppError
from app.db import models
from app.db.portability import export_learner, wipe_learner
from app.kernel import question_replacements as replacements
from app.orchestrator import assessment_content
from tests.test_assessment_visibility import setup


async def link(db, learner_id, original, target):
    db.add(
        models.QuestionReplacement(
            learner_id=learner_id, original_id=original.id, replacement_id=target.id
        )
    )
    db.add(
        models.QuestionState(
            learner_id=learner_id,
            assessment_id=original.id,
            state="superseded",
            revision=1,
            reason="Corrected",
            updated_at="2026-10-08T00:00:00+00:00",
        )
    )
    await db.commit()


async def test_owned_chain_and_original_snapshot_identity(db, learner):
    original, own, foreign, other = await setup(db, learner)
    await link(db, learner.id, original, own)
    assert (await replacements.resolve(db, learner.id, original.id)).id == own.id
    assert (await replacements.resolve(db, other.id, original.id)).id == original.id
    before = await assessment_content.snapshot(db, original.id, learner.id)
    assert before["id"] == original.id and before["item_json"]["question"] == "Shared?"
    with pytest.raises(AppError):
        assessment_content.require_eligible(before)
    final = models.Assessment(
        owner_learner_id=learner.id, skill_id=own.skill_id, kind=own.kind, item_json=own.item_json
    )
    db.add(final)
    await db.commit()
    await link(db, learner.id, own, final)
    assert (await replacements.resolve(db, learner.id, original.id)).id == final.id
    assert (await replacements.selected(db, learner.id, final)).id == final.id
    assert await db.scalar(select(func.count()).select_from(models.AssessmentAttempt)) == 0
    assert await db.scalar(select(func.count()).select_from(models.MemoryState)) == 0


@pytest.mark.parametrize(
    "fault",
    ["foreign", "shared", "kind", "skill", "cycle", "active_predecessor", "suspended_target"],
)
async def test_broken_lineage_never_falls_back(db, learner, fault):
    original, own, foreign, _ = await setup(db, learner)
    target = foreign if fault == "foreign" else own
    if fault == "shared":
        own.owner_learner_id = None
    if fault == "kind":
        own.kind = "cloze"
    if fault == "skill":
        node = models.SkillNode(slug="other", title="Other", domain="ai_ml")
        db.add(node)
        await db.flush()
        own.skill_id = node.id
    await db.commit()
    await link(db, learner.id, original, target)
    if fault == "cycle":
        original.owner_learner_id = learner.id
        await link(db, learner.id, own, original)
    elif fault == "active_predecessor":
        state = await db.get(models.QuestionState, (learner.id, original.id))
        state.state = "active"
    elif fault == "suspended_target":
        db.add(
            models.QuestionState(
                learner_id=learner.id,
                assessment_id=own.id,
                state="suspended",
                revision=1,
                reason="Review",
                updated_at="2026-10-08T00:00:00+00:00",
            )
        )
    await db.commit()
    with pytest.raises(AppError):
        await replacements.resolve(db, learner.id, original.id)
    with pytest.raises(AppError):
        await replacements.selected(db, learner.id, target)


async def test_lineage_export_wipe_and_depth_limit(db, learner, db_path, monkeypatch):
    original, own, _, other = await setup(db, learner)
    await link(db, learner.id, original, own)
    monkeypatch.setattr(replacements, "MAX_CHAIN", 1)
    with pytest.raises(AppError):
        await replacements.resolve(db, learner.id, original.id)
    lid, oid = learner.id, other.id
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        assert export_learner(conn, lid)["question_replacement"][0]["replacement_id"] == own.id
        assert export_learner(conn, oid)["question_replacement"] == []
        assert wipe_learner(conn, lid)["question_replacement"] == 1
        assert conn.execute("SELECT id FROM assessment WHERE id=?", (original.id,)).fetchone()
        assert not conn.execute("PRAGMA foreign_key_check").fetchall()
