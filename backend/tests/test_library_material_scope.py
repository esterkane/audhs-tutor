from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CurriculumDraft, LearnerPreference, LearnerProfile
from app.kernel.learning_scope import REFERENCE_BEFORE


async def test_library_material_input_excludes_other_owners_and_retired_rows(
    client: AsyncClient, db: AsyncSession, learner: LearnerProfile
):
    other = LearnerProfile(display_name="Other synthetic learner")
    db.add(other)
    await db.flush()
    db.add(
        LearnerPreference(
            learner_id=learner.id, key=REFERENCE_BEFORE, value_json="2025-01-02", origin="explicit"
        )
    )
    for owner, date, label in [
        (learner.id, "2025-01-03", "Visible"),
        (learner.id, "2025-01-01", "Retired"),
        (other.id, "2025-01-03", "Other learner"),
    ]:
        db.add(
            CurriculumDraft(
                learner_id=owner,
                title=label,
                created_at=date,
                status="published",
                origin="knowledge_authored",
                payload_json={"authoring": {"notes": label}},
            )
        )
    await db.commit()
    response = await client.get("/api/curriculum/drafts")
    assert response.status_code == 200
    assert [row["title"] for row in response.json()["drafts"]] == ["Visible"]


async def test_current_reading_content_uses_visible_owner_and_latest_object(
    client: AsyncClient, db: AsyncSession, learner: LearnerProfile
):
    from app.db.models import LearningObject, SkillNode

    other = LearnerProfile(display_name="Other synthetic owner")
    db.add(other)
    await db.flush()
    db.add(
        LearnerPreference(
            learner_id=learner.id, key=REFERENCE_BEFORE, value_json="2025-01-02", origin="explicit"
        )
    )
    skill = SkillNode(domain="programming", slug="synthetic-search-current", title="Visible skill")
    db.add(skill)
    await db.flush()
    for version, example in [
        (1, "Previously accepted phrasing"),
        (2, "Current independently revised example"),
    ]:
        db.add(
            LearningObject(
                skill_id=skill.id,
                version=version,
                concept="Concept",
                goal="current object-only goal",
                examples_json=["A current explanation", example],
            )
        )
    for index, (owner, date, published, notes) in enumerate(
        [
            (learner.id, "2025-01-03", "2025-01-04", "older same-timestamp edition"),
            (learner.id, "2025-01-03", "2025-01-04", "current personal notes"),
            (other.id, "2025-01-03", "2025-01-05", "other person's secret"),
            (learner.id, "2025-01-01", "2025-01-06", "archived pre-reset text"),
        ]
    ):
        db.add(
            CurriculumDraft(
                id=f"tie-check-{index}",
                learner_id=owner,
                title="Lesson",
                created_at=date,
                published_at=published,
                status="published",
                origin="knowledge_authored",
                payload_json={
                    "skills": [{"slug": skill.slug}],
                    "authoring": {
                        "notes": notes,
                        "worked_example": "Previously accepted phrasing",
                        "worked_example_prequestion": "Superseded question",
                    },
                },
            )
        )
    hidden = SkillNode(
        owner_learner_id=other.id,
        domain="programming",
        slug="hidden-private-skill",
        title="Private",
    )
    db.add(hidden)
    await db.flush()
    db.add(
        LearningObject(
            skill_id=hidden.id, version=1, concept="Private", goal="hidden object-only goal"
        )
    )
    db.add(
        CurriculumDraft(
            learner_id=learner.id,
            title="Stale pointer",
            origin="knowledge_authored",
            status="published",
            created_at="2025-01-03",
            published_at="2025-01-04",
            payload_json={"skills": [{"slug": hidden.slug}]},
        )
    )
    await db.commit()
    reading = await client.get(f"/api/knowledge-material/skills/{skill.id}/reading")
    assert reading.status_code == 200
    assert reading.json()["notes"] == "current personal notes"
    assert reading.json()["worked_example"] == "Current independently revised example"
    for term in [
        "current object-only goal",
        "current independently revised example",
        "current personal notes",
        "Previously accepted phrasing",
        "other person's secret",
        "archived pre-reset text",
        "hidden object-only goal",
        "Superseded question",
        "older same-timestamp edition",
    ]:
        response = await client.get(
            "/api/knowledge-material/library/lesson-matches", params={"q": term}
        )
        assert response.status_code == 200
        assert response.json() == ([skill.id] if term.startswith("current") else [])
