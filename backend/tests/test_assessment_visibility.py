"""Ownership is independent of practice state; shared caches never reuse private rows."""

import sqlite3
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.core.errors import AppError
from app.db import models
from app.db.portability import export_learner, wipe_learner
from app.kernel import correction_drafts, exercises, listening, review_content
from app.kernel import question_state as qs
from app.orchestrator import assessment_content, challenge
from app.orchestrator.grader import Grader
from tests.test_exercises import _node
from tests.test_question_state import action, item


async def setup(db, learner):
    shared = await item(db)
    shared.item_json = {"question": "Shared?", "options": ["A", "B"], "answer": 0}
    other = models.LearnerProfile(display_name="Other")
    db.add(other)
    await db.flush()
    own = models.Assessment(
        skill_id=shared.skill_id,
        kind="mcq",
        owner_learner_id=learner.id,
        item_json={"question": "Private?", "options": ["A", "B"], "answer": 1},
    )
    foreign = models.Assessment(
        skill_id=shared.skill_id,
        kind="mcq",
        owner_learner_id=other.id,
        item_json={"question": "Foreign secret", "options": ["A", "B"], "answer": 0},
    )
    db.add_all([own, foreign])
    await db.commit()
    return shared, own, foreign, other


async def test_visibility_and_eligibility_are_independent(db, learner):
    shared, own, foreign, _ = await setup(db, learner)

    def ids(rows):
        return {row.id for row in rows}

    assert ids(await db.scalars(select(models.Assessment).where(qs.visible(None)))) == {shared.id}
    assert ids(await db.scalars(select(models.Assessment).where(qs.visible(learner.id)))) == {
        shared.id,
        own.id,
    }
    await qs.transition(db, learner.id, own.id, action())
    await db.commit()
    assert await Grader(db, None).next_item(learner.id, shared.skill_id) == shared
    assert ids(
        await db.scalars(
            select(models.Assessment).where(qs.visible(learner.id), ~qs.eligible(learner.id))
        )
    ) == {own.id}
    for fn in [
        lambda: qs.read(db, learner.id, foreign.id),
        lambda: assessment_content.snapshot(db, foreign.id, learner.id),
        lambda: correction_drafts.original(db, foreign.id, learner.id),
        lambda: assessment_content.snapshot(db, own.id),
        lambda: qs.transition(db, learner.id, foreign.id, action()),
    ]:
        with pytest.raises(AppError) as error:
            await fn()
        assert error.value.http_status == 404


async def test_review_denies_cached_private_fallback_but_preserves_vocab(db, learner):
    shared, _, foreign, _ = await setup(db, learner)
    for kind in ["mcq", "vocab"]:
        card = models.ReviewItem(
            learner_id=learner.id,
            skill_id=shared.skill_id,
            item_type=kind,
            prompt_json={"type": kind, "ref": foreign.id, "q": "Cached secret", "a": "Vocabulary"},
        )
        db.add(card)
        await db.commit()
        eligible = await db.scalar(
            select(models.ReviewItem.id).where(
                models.ReviewItem.id == card.id, qs.review_eligible(learner.id)
            )
        )
        if kind == "mcq":
            assert eligible is None
            with pytest.raises(AppError) as error:
                await review_content.snapshot(db, learner.id, card.id)
            assert error.value.http_status == 404
        else:
            assert eligible == card.id
            assert (await review_content.snapshot(db, learner.id, card.id))["display"][
                "reveal"
            ] == "Vocabulary"


async def test_foreign_challenge_does_not_block_or_leak_into_reuse(db, learner):
    shared, own, foreign, other = await setup(db, learner)
    foreign.kind = "challenge_steelman"
    await db.commit()
    node = await db.get(models.SkillNode, shared.skill_id)
    assert (
        await challenge.reusable(db, SimpleNamespace(learner_id=learner.id), node, "steelman")
        is None
    )
    own.kind = "challenge_steelman"
    own.item_json = {"prompt": "Own challenge", "criteria": [], "sources": []}
    await db.commit()
    result = await challenge.reusable(db, SimpleNamespace(learner_id=learner.id), node, "steelman")
    assert result.assessment_id == own.id
    assert (await challenge.existing(db, other.id, node, "steelman")).id == foreign.id


async def test_canonical_exercise_and_listening_cache_ignore_owned_rows(db, learner):
    node = await _node(db)
    ex = exercises.for_slug(node.slug)
    private_check = models.Assessment(
        owner_learner_id=learner.id,
        skill_id=node.id,
        kind="explain_back",
        item_json={"exercise_id": ex.exercise_id, "prompt": "Private check"},
    )
    private_code = models.Assessment(
        owner_learner_id=learner.id,
        skill_id=node.id,
        kind="code",
        item_json={"exercise_id": ex.exercise_id},
    )
    private_clip = models.Assessment(
        owner_learner_id=learner.id,
        skill_id=node.id,
        kind="cloze",
        item_json={"listening": {"chunk_id": "synthetic"}},
    )
    db.add_all([private_check, private_code, private_clip])
    await db.commit()
    assert await listening.existing_task(db, node.id, "synthetic") is None
    code = await exercises.ensure_exercise(db, node)
    assert code.id != private_code.id and code.owner_learner_id is None
    assert code.item_json["check_assessment_id"] != private_check.id
    assert (await exercises.ensure_exercise(db, node)).id == code.id
    with pytest.raises(AppError):
        await listening.validate_task(db, private_clip.id, validated=True)
    assert "validated" not in private_clip.item_json["listening"]


async def test_private_export_wipe_and_restrictive_owner_fk(db, learner, db_path):
    shared, own, foreign, other = await setup(db, learner)
    rubric = models.AssessmentRubric(criteria_json=[{"criterion": "Private criterion"}])
    db.add(rubric)
    await db.flush()
    own.rubric_id = rubric.id
    db.add(
        models.AssessmentAttempt(learner_id=learner.id, assessment_id=own.id, answer="Historical")
    )
    await db.commit()
    lid, oid, own_id, rubric_id = learner.id, other.id, own.id, rubric.id
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("DELETE FROM learner_profile WHERE id=?", (lid,))
        conn.rollback()
        exported = export_learner(conn, lid)
        assert [r["id"] for r in exported["assessment"]] == [own_id]
        assert [r["id"] for r in exported["assessment_rubric"]] == [rubric_id]
        wiped = wipe_learner(conn, lid)
        assert wiped["assessment"] == wiped["assessment_rubric"] == 1
        assert {r[0] for r in conn.execute("SELECT id FROM assessment")} == {shared.id, foreign.id}
        assert export_learner(conn, oid)["assessment"][0]["id"] == foreign.id
        assert not conn.execute("PRAGMA foreign_key_check").fetchall()


async def test_direct_api_paths_hide_foreign_private_content(client, db):
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    s = await db.get(models.Session, session["id"])
    learner = await db.get(models.LearnerProfile, s.learner_id)
    _, _, foreign, _ = await setup(db, learner)
    for path in [
        f"/api/questions/{foreign.id}/practice",
        f"/api/questions/{foreign.id}/correction-source",
        f"/api/assess/items/{foreign.id}?session_id={s.id}",
    ]:
        response = await client.get(path)
        assert response.status_code == 404, response.text
        assert "Foreign secret" not in response.text
    response = await client.post(
        "/api/areas/feedback/questions",
        json={"assessment_id": foreign.id, "verdict": "bad", "labels": ["too_vague"]},
    )
    assert response.status_code == 404
    foreign.kind = "code"
    await db.commit()
    for suffix, body in [
        ("hint", {"session_id": s.id, "level": 1}),
        ("solution", {"session_id": s.id}),
    ]:
        assert (
            await client.post(f"/api/exercises/{foreign.id}/{suffix}", json=body)
        ).status_code == 404
    response = await client.post(
        "/api/assess/attempt",
        json={
            "session_id": s.id,
            "assessment_id": foreign.id,
            "answer": "x",
            "content_version": "invalid",
        },
    )
    assert response.status_code == 404, response.text
