from sqlalchemy import func, select

from app.db.models import CompetencyEvidence, KnowledgeArea, LearningEvent, SkillNode


async def test_area_concepts_uses_exact_membership_without_learning_writes(client, db):
    db.add_all(
        [
            KnowledgeArea(id="first", slug="first", title="First"),
            KnowledgeArea(id="empty", slug="empty", title="Empty"),
        ]
    )
    await db.flush()
    db.add_all(
        [
            SkillNode(
                id="member",
                slug="member",
                title="Actual concept",
                domain="test",
                area_id="first",
                description="Explain the mechanism",
                success_criteria_json=["Compare two examples"],
            ),
            SkillNode(id="similar", slug="similar", title="First similar title", domain="test"),
            SkillNode(
                id="deck",
                slug="deck",
                title="Deck",
                domain="test",
                area_id="first",
                assessment_requirements_json={"teachable": False},
            ),
        ]
    )
    await db.commit()
    before = [
        await db.scalar(select(func.count()).select_from(model))
        for model in [LearningEvent, CompetencyEvidence]
    ]
    response = await client.get("/api/areas/first/concepts")
    assert response.status_code == 200, response.text
    assert response.json() == {
        "area_id": "first",
        "concepts": [
            {
                "id": "member",
                "title": "Actual concept",
                "description": "Explain the mechanism",
                "success_criteria": ["Compare two examples"],
            }
        ],
    }
    assert (await client.get("/api/areas/empty/concepts")).json()["concepts"] == []
    assert (await client.get("/api/areas/missing/concepts")).status_code == 404
    assert [
        await db.scalar(select(func.count()).select_from(model))
        for model in [LearningEvent, CompetencyEvidence]
    ] == before
