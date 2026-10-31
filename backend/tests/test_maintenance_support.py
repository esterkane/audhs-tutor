from datetime import UTC, datetime, timedelta

import pytest

from app.kernel import adaptation, planner, preferences
from app.kernel import session as sessions
from app.schemas.common import Mode


def test_maintenance_plans_never_add_new_content_or_challenges():
    plan = planner.plan_session(
        planner.PlanInput(
            mode="novelty",
            energy=5,
            due_reviews=30,
            next_skill_id="new",
            review_node_ids=["a", "b", "c", "d"],
            preferences={"planner.maintenance": True},
        )
    )
    assert plan.types() == ["retrieval", "recap"]
    assert plan.blocks[0].node_ids == ["a", "b", "c"]
    assert plan.total_min <= 8
    assert "maintenance" in plan.blocks[0].reason


async def seed_sessions(db, learner, energies, same_day=False):
    now = datetime.now(UTC)
    for i, energy in enumerate(energies):
        s = await sessions.start(db, learner.id, mode=Mode.STEADY, energy=energy)
        await sessions.end(db, s.id, energy_after=None, self_report=None)
        s.started_at = (now - timedelta(days=0 if same_day else len(energies) - i)).isoformat()
        await db.commit()


async def test_support_requires_repeated_decline_and_does_not_apply_itself(db, learner):
    await seed_sessions(db, learner, [4, 4, 4, 2, 2, 1])
    offer = await adaptation.maintenance_support(db, learner.id, {})
    assert offer and offer.pref == "planner.maintenance"
    assert "not a diagnosis" in offer.why
    assert await preferences.get(db, learner.id, "planner.maintenance") is False
    card = await adaptation.propose(
        db,
        learner.id,
        what=offer.what,
        why=offer.why,
        pref=offer.pref,
        value=offer.value,
        pattern=offer.pattern,
        evidence=offer.evidence,
    )
    current = await sessions.start(db, learner.id, mode=Mode.STEADY, energy=3)
    before = list(current.planned_blocks_json or [])
    with pytest.raises(Exception, match="current plan stays unchanged"):
        await adaptation.decide(db, learner.id, card.id, "try", session=current)
    await adaptation.decide(db, learner.id, card.id, "default", session=current)
    assert await preferences.get(db, learner.id, "planner.maintenance") is True
    assert current.planned_blocks_json == before
    assert (
        await adaptation.maintenance_support(db, learner.id, {"planner.maintenance": True}) is None
    )
    await adaptation.undo(db, learner.id, card.id, session=current)
    assert await preferences.get(db, learner.id, "planner.maintenance") is False


@pytest.mark.parametrize(
    "energies,same_day", [([2, 2, 2, 2, 2, 2], False), ([4, 4, 4, 1, 1, 1], True), ([4, 1], False)]
)
async def test_low_baseline_one_day_or_sparse_data_do_not_imply_decline(
    db, learner, energies, same_day
):
    await seed_sessions(db, learner, energies, same_day)
    assert await adaptation.maintenance_support(db, learner.id, {}) is None


@pytest.mark.parametrize("value", [None, 42, {}, "x" * 301])
def test_start_cue_validation(value):
    with pytest.raises(ValueError):
        preferences.validate("session.next_start_cue", value)


async def test_preference_and_preview_require_explicit_choice(client, db):
    before = await client.get("/api/plan/preview?mode=steady&energy=3")
    assert before.status_code == 200
    result = await client.put(
        "/api/preferences", json={"key": "planner.maintenance", "value": True}
    )
    assert result.status_code == 200
    plan = (await client.get("/api/plan/preview?mode=steady&energy=3")).json()
    assert [b["type"] for b in plan["blocks"]] == ["retrieval", "recap"]
    assert (
        await client.put(
            "/api/preferences",
            json={"key": "session.next_start_cue", "value": "After opening, recall one question."},
        )
    ).status_code == 200
    assert (
        (await client.get("/api/preferences"))
        .json()["values"]["session.next_start_cue"]
        .startswith("After opening")
    )


async def test_new_maintenance_session_uses_three_item_cap_and_recap_minimum(client):
    await client.put("/api/preferences", json={"key": "planner.maintenance", "value": True})
    response = await client.post("/api/sessions", json={"mode": "steady", "energy": 5})
    assert response.status_code == 200 or response.status_code == 201
    session = response.json()
    assert session["review_cap"] == 3
    assert session["minimum_viable"] == ["retrieval", "recap"]
    await client.put("/api/preferences", json={"key": "planner.maintenance", "value": False})
    reread = (await client.get("/api/sessions/" + session["id"])).json()
    assert reread["review_cap"] == 3  # the persisted session retains its chosen plan
    due = (await client.get("/api/review/due?session_id=" + session["id"])).json()
    assert due["cap"] == 3


async def test_explicit_lesson_request_does_not_end_saved_work_during_maintenance(client):
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    await client.put("/api/preferences", json={"key": "planner.maintenance", "value": True})
    result = await client.get("/api/sessions/selection/selected-lesson")
    assert result.status_code == 409
    assert result.json()["error"]["code"] == "maintenance_planning"
    current = (await client.get("/api/sessions/current")).json()
    assert current["id"] == session["id"] and current["ended_at"] is None
