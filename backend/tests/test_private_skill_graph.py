"""Skill graph scope must apply before ranking, traversal and direct selection."""

import pytest
from sqlalchemy import select, text

from app.db.models import LearnerProfile, LearningObject, SkillEdge, SkillNode
from app.kernel import skill_graph


async def test_graph_scope_and_hidden_prerequisites(db, learner):
    db.add(LearnerProfile(id="other", display_name="Other"))
    await db.flush()
    for name, owner in [("shared", None), ("own", learner.id), ("foreign", "other")]:
        db.add(
            SkillNode(
                id=name, slug=name, domain="ai_ml", title=name, owner_learner_id=owner, course=name
            )
        )
    await db.flush()
    db.add(LearningObject(id="foreign-object", skill_id="foreign", concept="secret", goal="secret"))
    db.add(LearningObject(id="own-object", skill_id="own", concept="owned", goal="owned"))
    db.add(SkillEdge(from_skill_id="shared", to_skill_id="own", kind="related"))
    db.add(SkillEdge(from_skill_id="shared", to_skill_id="foreign", kind="related"))
    await db.commit()
    assert {n.id for n in await skill_graph.all_nodes(db)} == {"shared"}
    assert await skill_graph.all_edges(db) == []
    assert await skill_graph.get_node_by_slug(db, "foreign", learner_id=learner.id) is None
    assert await skill_graph.learning_object_for(db, "foreign", learner_id=learner.id) is None
    assert (
        await skill_graph.learning_object_for(db, "own", learner_id=learner.id)
    ).id == "own-object"
    assert await skill_graph.learning_object_for(db, "own") is None
    for name in ["missing", "foreign"]:
        with pytest.raises(KeyError):
            await skill_graph.selection(db, learner.id, name)
        with pytest.raises(KeyError):
            await skill_graph.prerequisites(db, name, learner_id=learner.id)
    view = await skill_graph.map_view(db, learner.id)
    assert {n["id"] for n in view["nodes"]} == {"shared", "own"}
    assert view["edges"] == [{"from": "shared", "to": "own", "kind": "related"}]
    assert "foreign" not in view["mermaid"]
    assert await skill_graph.next_skill(db, learner.id, goals={"goal.course": "foreign"}) is None
    assert await skill_graph.goal_scope(db, learner.id, goals={"goal.course": "foreign"}) == []
    assert (await skill_graph.selection(db, learner.id, "own"))[0].id == "own"
    # Deliberately bypass the storage guard to exercise defensive reads.
    await db.execute(text("DROP TRIGGER skill_edge_owner_insert"))
    # Before storage guards land, a malformed hidden dependency must fail closed.
    db.add(SkillEdge(from_skill_id="foreign", to_skill_id="own", kind="prerequisite"))
    await db.commit()
    assert not await skill_graph.is_unlocked(db, learner.id, "own")
    assert await skill_graph.next_skill(db, learner.id, goals={"goal.course": "own"}) is None
    assert await skill_graph.goal_scope(db, learner.id, goals={"goal.course": "own"}) == ["own"]
    assert {n.id for n in await skill_graph.topological_order(db, learner_id="other")} == {
        "shared",
        "foreign",
    }
    owned = await db.get(SkillNode, "own")
    owned.domain = "language"
    await db.commit()
    assert await skill_graph.next_skill(db, learner.id, "language", goals={}) is None
    assert len(list(await db.scalars(select(SkillNode)))) == 3


async def test_skill_routes_hide_foreign_content_and_refuse_bookmarks(client, db, learner):
    from app.db.models import LearnerPreference

    db.add(LearnerProfile(id="other", display_name="Other", created_at="2999-01-01"))
    await db.flush()
    db.add(
        SkillNode(
            id="own", slug="own", title="Owned lesson", domain="ai_ml", owner_learner_id=learner.id
        )
    )
    db.add(
        SkillNode(
            id="foreign",
            slug="foreign",
            title="Secret lesson",
            domain="ai_ml",
            owner_learner_id="other",
        )
    )
    await db.commit()
    listing = await client.get("/api/skills")
    assert listing.status_code == 200
    assert {s["id"] for s in listing.json()["skills"]} == {"own"}
    mapped = await client.get("/api/skills/map")
    assert mapped.status_code == 200
    assert "Secret lesson" not in mapped.text
    assert (await client.get("/api/skills/own")).status_code == 200
    for target in ["missing", "foreign"]:
        assert (await client.get(f"/api/skills/{target}")).status_code == 404
        assert (await client.get(f"/api/skills/{target}/evidence")).status_code == 404
        assert (
            await client.put(f"/api/skills/{target}/mark", json={"status": "clear"})
        ).status_code == 404
    assert not list(
        await db.scalars(
            select(LearnerPreference).where(LearnerPreference.key == "learning.material_marks")
        )
    )
