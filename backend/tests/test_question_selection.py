"""Selectors exclude suspended identities without regenerating their canonical content."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.errors import AppError
from app.db import models
from app.kernel import listening, question_state
from app.orchestrator import challenge
from app.orchestrator import listening as listening_gen
from app.orchestrator.grader import Grader
from app.schemas.question_state import QuestionTransitionIn
from tests.test_exercises import _node


async def suspend(db, learner_id, assessment_id):
    await question_state.transition(
        db,
        learner_id,
        assessment_id,
        QuestionTransitionIn(request_id=uuid4(), action="suspend", expected_revision=0),
    )
    await db.commit()


async def test_ordinary_selection_skips_suspended_and_returns_none_when_exhausted(db, learner):
    node = await _node(db)
    items = list(
        (
            await db.scalars(select(models.Assessment).where(models.Assessment.skill_id == node.id))
        ).all()
    )
    first = await Grader(db, None).next_item(learner.id, node.id)
    await suspend(db, learner.id, first.id)
    for _ in range(3):
        selected = await Grader(db, None).next_item(learner.id, node.id)
        assert selected is None or selected.id != first.id
    for item in items:
        if item.id != first.id:
            await suspend(db, learner.id, item.id)
    assert await Grader(db, None).next_item(learner.id, node.id) is None


async def test_canonical_exercise_is_not_recreated_when_suspended(client, db):
    node = await _node(db)
    s = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    session = await db.get(models.Session, s["id"])
    route = f"/api/exercises/for-skill/{node.id}"
    response = await client.get(route)
    assert response.status_code == 200, response.text
    question_id = response.json()["assessment_id"]
    before = await db.scalar(select(func.count()).select_from(models.Assessment))
    await suspend(db, session.learner_id, question_id)
    assert (await client.get(route)).status_code == 409
    for suffix, body in [
        ("hint", {"session_id": session.id, "level": 1}),
        ("solution", {"session_id": session.id}),
    ]:
        assert (
            await client.post(f"/api/exercises/{question_id}/{suffix}", json=body)
        ).status_code == 409
    assert await db.scalar(select(func.count()).select_from(models.Assessment)) == before


async def test_suspended_linked_check_does_not_remove_code_workspace(client, db):
    node = await _node(db)
    s = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    session = await db.get(models.Session, s["id"])
    route = f"/api/exercises/for-skill/{node.id}"
    initial = (await client.get(route)).json()
    await suspend(db, session.learner_id, initial["check_assessment_id"])
    response = await client.get(route)
    assert response.status_code == 200
    current = response.json()
    assert current["starter_code"] == initial["starter_code"]
    assert current["check_assessment_id"] is None and current["check_content_version"] is None
    assert "unavailable" in current["check_question"]
    solution = await client.post(
        f"/api/exercises/{current['assessment_id']}/solution", json={"session_id": session.id}
    )
    assert solution.status_code == 200 and "unavailable" in solution.json()["check_question"]


async def test_challenge_reuse_and_generation_do_not_resurrect_suspended_item(db, learner):
    node = await _node(db)
    a = models.Assessment(
        skill_id=node.id, kind="challenge_steelman", item_json={"prompt": "Synthetic"}
    )
    db.add(a)
    await db.commit()
    await suspend(db, learner.id, a.id)
    assert await challenge.existing(db, learner.id, node, "steelman") is None
    with pytest.raises(AppError):
        await challenge.start(
            db, None, None, SimpleNamespace(learner_id=learner.id), node, "steelman"
        )
    assert await db.get(models.Assessment, a.id) is not None


async def test_listening_canonical_reuse_blocks_before_generation_and_validation(db, learner):
    node = await listening.listening_node(db, "en")
    a = models.Assessment(
        skill_id=node.id,
        kind="cloze",
        item_json={
            "text": "Synthetic ____",
            "answers": ["signal"],
            "listening": {"chunk_id": "synthetic-chunk", "validated": False},
        },
    )
    db.add(a)
    await db.commit()
    await suspend(db, learner.id, a.id)
    with pytest.raises(AppError):
        await listening_gen.ensure_task(
            db,
            None,
            lesson=SimpleNamespace(language="en"),
            section=SimpleNamespace(chunk_id="synthetic-chunk"),
            learner_id=learner.id,
            session_id="unused",
            use_model=True,
        )
    with pytest.raises(AppError):
        await listening.validate_task(db, a.id, validated=True, learner_id=learner.id)
    await db.refresh(a)
    assert a.item_json["listening"]["validated"] is False
    assert (
        await db.scalar(
            select(func.count())
            .select_from(models.Assessment)
            .where(models.Assessment.skill_id == node.id)
        )
        == 1
    )


async def test_session_stop_chooses_eligible_recall_despite_old_suspended_card(client, db):
    from app.api.sessions import ensure_recall_item_for_explained_skill
    from app.db.events import EventWriter, Verb
    from app.kernel import memory
    from app.kernel import session as sessions
    from app.schemas.common import ObjectType

    node = await _node(db)
    s = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    session = await db.get(models.Session, s["id"])
    await sessions.save_checkpoint(db, session, {"skill_id": node.id})
    await EventWriter(db, sessions.event_context(session)).emit(
        Verb.EXPLAINED,
        ObjectType.NODE,
        node.id,
        result={"sentences": 1, "cited_sources": []},
        context={"node_id": node.id},
    )
    items = list(
        (
            await db.scalars(select(models.Assessment).where(models.Assessment.skill_id == node.id))
        ).all()
    )
    assert len(items) > 1
    old = items[0]
    await memory.ensure_item(db, session.learner_id, node.id, old.kind, {"ref": old.id})
    await suspend(db, session.learner_id, old.id)
    await ensure_recall_item_for_explained_skill(db, session.learner_id, session.id)
    due = await memory.due_items(db, session.learner_id)
    assert len(due) == 1 and due[0][0].prompt_json["assessment_id"] != old.id
    for item in items[1:]:
        await suspend(db, session.learner_id, item.id)
    before = await db.scalar(select(func.count()).select_from(models.ReviewItem))
    await ensure_recall_item_for_explained_skill(db, session.learner_id, session.id)
    assert await memory.due_items(db, session.learner_id) == []
    assert await db.scalar(select(func.count()).select_from(models.ReviewItem)) == before
