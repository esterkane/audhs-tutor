"""Source availability is not learner-specific lesson readiness."""

from app.db.models import KnowledgeArea, SkillEdge, SkillNode
from app.kernel import areas


async def test_catalogue_distinguishes_empty_available_prerequisite_and_blocked(db, learner):
    names = ["empty", "ready", "prerequisite", "blocked"]
    db.add_all([KnowledgeArea(id=name, slug=name, title=name, terms_json=[name]) for name in names])
    nodes = [
        SkillNode(id="open", slug="open", title="Open", domain="ai_ml", area_id="ready"),
        SkillNode(id="pre", slug="pre", title="Prerequisite", domain="ai_ml"),
        SkillNode(
            id="target", slug="target", title="Target", domain="ai_ml", area_id="prerequisite"
        ),
        SkillNode(
            id="not-teachable",
            slug="not-teachable",
            title="Deck",
            domain="language",
            assessment_requirements_json={"teachable": False},
        ),
        SkillNode(
            id="blocked-target",
            slug="blocked-target",
            title="Blocked",
            domain="ai_ml",
            area_id="blocked",
        ),
        SkillNode(
            id="empty-deck",
            slug="empty-deck",
            title="Deck",
            domain="language",
            area_id="empty",
            assessment_requirements_json={"teachable": False},
        ),
    ]
    db.add_all(nodes)
    await db.flush()
    db.add_all(
        [
            SkillEdge(from_skill_id="pre", to_skill_id="target"),
            SkillEdge(from_skill_id="not-teachable", to_skill_id="blocked-target"),
        ]
    )
    await db.flush()
    result = {row["id"]: row for row in (await areas.catalogue(db, learner.id))["areas"]}
    assert [result[name]["active_lessons"] for name in names] == [0, 1, 1, 1]
    # Activation count never labels locked lessons as available; only /skills selects eligibility.
    assert all("available_lessons" not in row and "readiness" not in row for row in result.values())
