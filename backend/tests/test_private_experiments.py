"""Foreign units must not affect experiment balancing, counts or outcomes."""

import pytest
from sqlalchemy import func, select

from app.core.errors import AppError
from app.db.models import ExperimentAssignment, LearnerProfile, LearningEvent, SkillNode
from app.kernel import experiments


async def test_foreign_assignments_are_denied_and_legacy_rows_excluded(db, learner, client):
    learner_id = learner.id
    db.add(LearnerProfile(id="other", display_name="Other"))
    await db.flush()
    for name, owner in [("shared", None), ("own", learner_id), ("foreign", "other")]:
        db.add(SkillNode(id=name, slug=name, title=name, domain="ai_ml", owner_learner_id=owner))
    await db.commit()
    exp = await experiments.from_template(db, learner_id, "socratic-vs-explicit")
    await experiments.start(db, learner_id, exp.id)
    arms = await experiments.arms_of(db, exp.id)
    before = await db.scalar(select(func.count()).select_from(LearningEvent))
    with pytest.raises(AppError) as error:
        await experiments.assign(db, learner_id, exp, unit_id="foreign")
    assert error.value.http_status == 404
    assert await db.scalar(select(func.count()).select_from(ExperimentAssignment)) == 0
    assert await db.scalar(select(func.count()).select_from(LearningEvent)) == before
    # Deliberately invalid legacy assignments: foreign target and foreign row owner.
    for owner, unit in [(learner_id, "foreign"), ("other", "shared")]:
        db.add(
            ExperimentAssignment(
                learner_id=owner,
                experiment_id=exp.id,
                arm_id=arms[0].id,
                unit_type="node",
                unit_id=unit,
            )
        )
    await db.commit()
    assert await experiments.visible_assignments(db, learner_id, exp.id) == []
    assert await experiments.unit_outcomes(db, learner_id, exp) == {}
    results = await experiments.results(db, learner_id, exp.id)
    assert sum(results.assignments.values()) == 0 and results.units_without_data == 0
    # A hidden conflicting assignment must not become an idempotent success.
    with pytest.raises(AppError) as conflict:
        await experiments.assign(db, learner_id, exp, unit_id="shared")
    assert conflict.value.http_status == 409
    response = await client.get(f"/api/experiments/{exp.id}/results")
    assert response.status_code == 200
    assert response.json()["units"] == []
    assert sum(a["assigned"] for a in response.json()["experiment"]["arms"]) == 0
    with pytest.raises(KeyError):
        await experiments.visible_assignments(db, "other", exp.id)
    # Owned nodes and missing historical unit IDs retain normal balanced assignment.
    for unit in ["own", "legacy-unlinked"]:
        await experiments.assign(db, learner_id, exp, unit_id=unit)
    visible = await experiments.visible_assignments(db, learner_id, exp.id)
    assert {a.unit_id for a in visible} == {"own", "legacy-unlinked"}
    assert len({a.arm_id for a in visible}) == 2


async def test_foreign_session_and_experiment_context_cannot_be_assigned(db, learner):
    from app.db.models import Session

    db.add(LearnerProfile(id="other", display_name="Other"))
    await db.flush()
    foreign_session = Session(id="foreign-session", learner_id="other", mode="steady", energy=3)
    db.add(foreign_session)
    await db.commit()
    exp = await experiments.create(
        db,
        learner.id,
        name="Session comparison",
        hypothesis="Compare",
        metric="completion",
        unit_type="session",
        arms=[{"name": "A"}, {"name": "B"}],
    )
    with pytest.raises(AppError):
        await experiments.assign(db, learner.id, exp, unit_id=foreign_session.id)
    with pytest.raises(AppError):
        await experiments.assign(db, learner.id, exp, unit_id="legacy", session=foreign_session)
    with pytest.raises(KeyError):
        await experiments.assign(db, "other", exp, unit_id="legacy")
    assert await db.scalar(select(func.count()).select_from(ExperimentAssignment)) == 0
    arm = (await experiments.arms_of(db, exp.id))[0]
    db.add(
        ExperimentAssignment(
            learner_id=learner.id,
            experiment_id=exp.id,
            arm_id=arm.id,
            unit_type="session",
            unit_id=foreign_session.id,
        )
    )
    await db.commit()
    assert await experiments.visible_assignments(db, learner.id, exp.id) == []
    assert await experiments.unit_outcomes(db, learner.id, exp) == {}
