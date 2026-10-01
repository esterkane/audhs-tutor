from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.kernel import competency, planner, preferences, representations, skill_graph
from app.kernel.seed import load_seed

SEED = Path(__file__).resolve().parents[2] / "seeds" / "attention"


def test_planner_valid_for_every_mode_energy_combo() -> None:
    for mode in ("novelty", "steady", "low_capacity"):
        for energy in range(1, 6):
            for due in (0, 7):
                p = planner.plan_session(
                    planner.PlanInput(
                        mode=mode,
                        energy=energy,
                        due_reviews=due,
                        next_skill_id="k1",
                        review_node_ids=["a", "b"] if due else [],
                    )
                )
                planner.validate_plan(p)  # raises on any invariant violation
                assert p.types()[-1] == "recap" and "retrieval" in p.types()
                assert p.minimum_viable == ["retrieval", "recap"]
                assert 10 <= p.total_min <= 90
    a = planner.plan_session(planner.PlanInput(mode="steady", energy=3, next_skill_id="k1"))
    b = planner.plan_session(planner.PlanInput(mode="steady", energy=3, next_skill_id="k1"))
    assert a == b  # deterministic


def test_planner_rules() -> None:
    low = planner.plan_session(
        planner.PlanInput(
            mode="low_capacity", energy=2, due_reviews=5, next_skill_id="k1", review_node_ids=["a"]
        )
    )
    assert low.types() == ["retrieval", "interleaved_review", "recap"] and low.total_min <= 25
    low_new = planner.plan_session(
        planner.PlanInput(mode="low_capacity", energy=2, due_reviews=0, next_skill_id="k1")
    )
    assert low_new.types() == ["retrieval", "new_material", "recap"]
    steady = planner.plan_session(
        planner.PlanInput(
            mode="steady",
            energy=4,
            due_reviews=3,
            next_skill_id="k1",
            next_skill_mastery=0.4,
            review_node_ids=["a"],
        )
    )
    assert steady.types() == [
        "movement_primer",
        "retrieval",
        "new_material",
        "challenge",
        "interleaved_review",
        "recap",
    ]
    assert steady.blocks[2].grasp_check_required and steady.blocks[0].optional
    after = planner.plan_session(
        planner.PlanInput(
            mode="steady",
            energy=3,
            next_skill_id="k1",
            preferences={"planner.movement": "after", "planner.challenge": False},
        )
    )
    assert after.types() == ["retrieval", "new_material", "movement_primer", "recap"]
    novelty = planner.plan_session(
        planner.PlanInput(
            mode="novelty",
            energy=5,
            next_skill_id="k1",
            preferences={"planner.new_material_min": 25},
        )
    )
    assert novelty.blocks[2].planned_min == 36 and novelty.blocks[2].type == "new_material"
    with pytest.raises(ValueError, match="recap"):
        planner.validate_plan(
            planner.Plan(
                mode="steady",
                energy=3,
                blocks=[planner.Block(type="retrieval", planned_min=5)],
                minimum_viable=[],
                total_min=5,
            )
        )
    ok, why = planner.can_switch_early(steady.blocks[2], grasp_passed=None, reason="bored")
    assert not ok and "grasp" in why
    assert planner.can_switch_early(steady.blocks[2], grasp_passed=True, reason="bored")[0]
    assert planner.can_switch_early(steady.blocks[2], grasp_passed=None, reason="save_and_stop")[0]


async def test_preferences_registry(db: AsyncSession, learner: models.LearnerProfile) -> None:
    prefs = await preferences.get_all(db, learner.id)
    assert prefs["planner.new_material_min"] == 20 and prefs["ui.reduced_motion"] is True
    await preferences.set_pref(db, learner.id, "planner.new_material_min", 30)
    await preferences.set_pref(db, learner.id, "session.socratic_default", True, origin="explicit")
    assert (await preferences.get_all(db, learner.id))["planner.new_material_min"] == 30
    with pytest.raises(ValueError, match="between"):
        await preferences.set_pref(db, learner.id, "planner.new_material_min", 99)
    with pytest.raises(ValueError, match="one of"):
        await preferences.set_pref(db, learner.id, "planner.movement", "sideways")
    with pytest.raises(ValueError, match="unknown preference"):
        await preferences.set_pref(db, learner.id, "chat.memory", "x")
    with pytest.raises(ValueError, match="boolean"):
        await preferences.set_pref(db, learner.id, "ui.sound", "yes")
    await preferences.reset(db, learner.id, "planner.new_material_min")
    assert (await preferences.get_all(db, learner.id))["planner.new_material_min"] == 20


async def test_representation_cache_and_map(
    db: AsyncSession, learner: models.LearnerProfile
) -> None:
    await load_seed(db, SEED)
    node = await skill_graph.get_node_by_slug(db, "attn-scaled")
    assert node
    obj = await representations.object_for_skill(db, node.id)
    assert obj is not None
    assert await representations.get_cached(db, obj.id, "analogy") is None
    row = await representations.store(
        db, obj.id, "analogy", "(analogy) like a volume knob", model_call_id=None
    )
    again = await representations.get_cached(db, obj.id, "analogy")
    assert again is not None and again.id == row.id and again.object_id == obj.id
    assert await representations.cached_kinds(db, obj.id) == {"analogy"}
    assert "problem_first" not in representations.allowed_kinds(
        0.2
    ) and "problem_first" in representations.allowed_kinds(0.7)
    with pytest.raises(ValueError):
        await representations.store(db, obj.id, "hologram", "x", model_call_id=None)
    assert await representations.invalidate(db, obj.id) == 1

    await competency.record_evidence(
        db, learner.id, node.id, "recall", 1.0, grader_level="deterministic"
    )
    await competency.refresh(db, learner.id, node.id)
    view = await skill_graph.map_view(db, learner.id)
    assert len(view["nodes"]) == 8 and len(view["edges"]) == 8
    scaled = next(n for n in view["nodes"] if n["slug"] == "attn-scaled")
    assert scaled["mastery"] > 0 and scaled["unlocked"] is False and "memory" in scaled
    assert sum(1 for n in view["nodes"] if n["is_next"]) == 1
    assert (
        view["mermaid"].startswith("graph LR")
        and ":::next" in view["mermaid"]
        and "-->" in view["mermaid"]
    )
