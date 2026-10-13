"""No private title/dimensions in linked contexts and no foreign reminder promotion."""

import pytest
from sqlalchemy import func, select

from app.core.errors import AppError
from app.db.models import LearnerProfile, ParkingLotItem, SkillNode, ThoughtAction
from app.kernel import competency, experiments


async def test_foreign_competency_and_reminder_links_are_denied(db, learner, client):
    db.add(LearnerProfile(id="other", display_name="Other", created_at="2999-01-01"))
    await db.flush()
    node = SkillNode(
        id="foreign",
        slug="foreign",
        title="Secret title",
        domain="ai_ml",
        owner_learner_id="other",
        assessment_requirements_json={"dimensions": ["transfer"]},
    )
    db.add(node)
    await db.commit()
    for operation in [competency.mastery, competency.skill_state]:
        with pytest.raises(AppError) as error:
            await operation(db, learner.id, node.id)
        assert error.value.http_status == 404
    # Unlinked historical experiment unit IDs keep their existing empty-state behavior.
    assert await competency.mastery(db, learner.id, "legacy-unlinked-unit") == 0
    saved = (await client.post("/api/parking", json={"text": "Remember"})).json()
    before = await db.scalar(select(func.count()).select_from(ThoughtAction))
    response = await client.post(
        f"/api/parking/{saved['id']}/actions",
        json={
            "request_key": "foreign-promote",
            "expected_revision": 0,
            "action": "promote",
            "promoted_to": node.id,
        },
    )
    assert response.status_code == 404
    assert await db.scalar(select(func.count()).select_from(ThoughtAction)) == before

    legacy = await client.post(f"/api/parking/{saved['id']}/promote", json={"promoted_to": node.id})
    assert legacy.status_code == 404
    assert await db.scalar(select(func.count()).select_from(ThoughtAction)) == before

    # An old invalid link can be removed, but undo must not restore it.
    item = await db.get(ParkingLotItem, saved["id"], populate_existing=True)
    item.node_id = node.id
    item.promoted_to = node.id
    item.status = "promoted"
    await db.commit()
    dropped = await client.post(
        f"/api/parking/{saved['id']}/actions",
        json={"request_key": "drop", "expected_revision": 0, "action": "drop"},
    )
    assert dropped.status_code == 200
    receipt = dropped.json()
    before_undo = await db.scalar(select(func.count()).select_from(ThoughtAction))
    undo = await client.post(
        f"/api/parking/{saved['id']}/actions",
        json={
            "request_key": "undo",
            "expected_revision": 1,
            "action": "undo",
            "undo_of": receipt["action_id"],
        },
    )
    assert undo.status_code == 409
    assert await db.scalar(select(func.count()).select_from(ThoughtAction)) == before_undo
    await db.refresh(item)
    assert item.status == "dropped" and item.revision == 1

    # Historical experiment assignments must not resolve foreign titles.
    exp = await experiments.from_template(db, learner.id, "socratic-vs-explicit")
    await experiments.assign(db, learner.id, exp, unit_id=node.id)
    response = await client.get(f"/api/experiments/{exp.id}/results")
    assert response.status_code == 200
    assert "Secret title" not in response.text
    assert response.json()["units"][0]["label"] == node.id


async def test_competency_writes_reject_foreign_skills_without_evidence(db, learner):
    from app.db.events import EventContext, EventWriter
    from app.db.models import CompetencyEvidence, CompetencyState, LearningEvent
    from app.schemas.common import Mode

    db.add(LearnerProfile(id="other", display_name="Other"))
    await db.flush()
    for name, owner in [("shared", None), ("own", learner.id), ("foreign", "other")]:
        db.add(SkillNode(id=name, slug=name, title=name, domain="ai_ml", owner_learner_id=owner))
    await db.commit()
    for name in ["shared", "own"]:
        await competency.record_evidence(
            db, learner.id, name, "explanation", 0.8, grader_level="deterministic"
        )
        state = await competency.refresh(db, learner.id, name)
        assert state["explanation"].count == 1
    tables = [CompetencyEvidence, CompetencyState, LearningEvent]
    before = [await db.scalar(select(func.count()).select_from(t)) for t in tables]
    for commit in [False, True]:
        with pytest.raises(AppError) as error:
            await competency.record_evidence(
                db,
                learner.id,
                "foreign",
                "explanation",
                1,
                grader_level="deterministic",
                events=EventWriter(
                    db,
                    EventContext(
                        learner_id=learner.id, session_id=None, mode=Mode.STEADY, energy=3
                    ),
                ),
                commit=commit,
            )
        assert error.value.http_status == 404
        with pytest.raises(AppError):
            await competency.refresh(db, learner.id, "foreign", commit=commit)
    with pytest.raises(AppError):
        await competency.states(db, learner.id, "foreign")
    after = [await db.scalar(select(func.count()).select_from(t)) for t in tables]
    assert before == after
    assert await competency.states(db, learner.id, "missing") == {}
