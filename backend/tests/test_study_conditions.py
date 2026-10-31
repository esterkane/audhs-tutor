from datetime import UTC, datetime, timedelta

from app.db.events import Verb
from app.kernel import session as sessions
from app.kernel import study_conditions
from app.schemas.common import Mode


async def append(db, session, verb, node, ts, result, obj="item"):
    from app.db.models import LearningEvent

    event = LearningEvent(
        learner_id=session.learner_id,
        session_id=session.id,
        ts=ts.isoformat(),
        actor="learner",
        verb=str(verb),
        object_type="item",
        object_id=obj,
        domain="programming",
        activity_type="review",
        mode="steady",
        energy=3,
        result_json=result,
        context_json={"node_id": node},
    )
    db.add(event)
    await db.commit()
    return event


async def condition(db, session, node, ts):
    await append(
        db,
        session,
        Verb.STUDY_CONDITIONS,
        node,
        ts,
        {
            "conditions": {
                "noise": "white",
                "presence": "alone",
                "movement": "none",
                "timer": "elapsed",
            }
        },
    )


async def test_delayed_distinct_item_observations_not_same_day_or_duplicate(db, learner):
    now = datetime.now(UTC)
    old = now - timedelta(days=3)
    first = await sessions.start(db, learner.id, mode=Mode.STEADY, energy=3)
    await condition(db, first, "node", old)
    await append(db, first, Verb.ATTEMPTED, "node", old + timedelta(minutes=1), {"correct": True})
    await append(
        db,
        first,
        Verb.REVIEWED,
        "node",
        old + timedelta(minutes=2),
        {"rating": 4, "days_since_learned": 0},
    )
    await sessions.end(db, first.id, energy_after=None, self_report=None)
    later = await sessions.start(db, learner.id, mode=Mode.STEADY, energy=3)
    await append(db, later, Verb.REVIEWED, "node", now, {"rating": 3, "days_since_learned": 3})
    await append(
        db,
        later,
        Verb.REVIEWED,
        "node",
        now + timedelta(seconds=1),
        {"rating": 4, "days_since_learned": 3},
    )
    result = await study_conditions.summary(db, learner.id)
    assert (
        len(result.groups) == 1
        and result.groups[0].items_reviewed == 1
        and result.groups[0].recalled == 1
    )
    assert "do not establish" in result.reading
    assert not (await study_conditions.summary(db, "another-learner")).groups


async def test_unrecorded_later_study_does_not_inherit_old_conditions(db, learner):
    now = datetime.now(UTC)
    old = now - timedelta(days=4)
    first = await sessions.start(db, learner.id, mode=Mode.STEADY, energy=3)
    await condition(db, first, "node", old)
    await append(db, first, Verb.ATTEMPTED, "node", old + timedelta(minutes=1), {"correct": True})
    await sessions.end(db, first.id, energy_after=None, self_report=None)
    second = await sessions.start(db, learner.id, mode=Mode.STEADY, energy=3)
    await append(db, second, Verb.ATTEMPTED, "node", old + timedelta(days=1), {"correct": True})
    await sessions.end(db, second.id, energy_after=None, self_report=None)
    third = await sessions.start(db, learner.id, mode=Mode.STEADY, energy=3)
    await append(db, third, Verb.REVIEWED, "node", now, {"rating": 3, "days_since_learned": 3})
    assert not (await study_conditions.summary(db, learner.id)).groups


async def test_record_requires_active_learner_owned_lesson_and_valid_conditions(client):
    created = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    response = await client.post(
        "/api/study-conditions",
        json={"session_id": created["id"], "conditions": {"noise": "magic"}},
    )
    assert response.status_code == 422
    response = await client.post(
        "/api/study-conditions", json={"session_id": "unavailable", "conditions": {}}
    )
    assert response.status_code in (404, 409)
    assert (await client.get("/api/study-conditions/summary")).json()["groups"] == []
