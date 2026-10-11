from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CompetencyEvidence, CompetencyState, LearnerProfile, SkillNode
from app.kernel.progress import evidence_page


async def test_evidence_is_dated_paginated_isolated_and_read_only(
    client: AsyncClient, db: AsyncSession, learner: LearnerProfile
) -> None:
    db.add(SkillNode(id="progress", slug="progress", title="Progress example", domain="test"))
    other = LearnerProfile(id="other-progress", display_name="Other")
    db.add(other)
    await db.flush()
    db.add_all(
        [
            CompetencyEvidence(
                id="older",
                learner_id=learner.id,
                skill_id="progress",
                dimension="explanation",
                score=0.5,
                ts="2026-01-01T00:00:00+00:00",
            ),
            CompetencyEvidence(
                id="newer",
                learner_id=learner.id,
                skill_id="progress",
                dimension="transfer",
                score=1,
                ts="2026-01-02T00:00:00+00:00",
            ),
            CompetencyEvidence(
                id="private-other",
                learner_id=other.id,
                skill_id="progress",
                dimension="application",
                score=1,
                ts="2026-01-03T00:00:00+00:00",
            ),
        ]
    )
    await db.commit()
    before = await db.scalar(select(func.count()).select_from(CompetencyState))
    response = await client.get("/api/skills/progress/evidence?limit=1")
    assert response.status_code == 200
    page = response.json()
    assert page["total"] == 2
    assert {row["dimension"]: row["count"] for row in page["dimensions"]} == {
        "explanation": 1,
        "transfer": 1,
    }
    assert [item["id"] for item in page["items"]] == ["newer"]
    assert page["items"][0]["recorded_at"] == "2026-01-02T00:00:00+00:00"
    assert page["items"][0]["independence"] == "not_verified"
    assert page["items"][0]["reported_hint_count"] is None
    assert page["items"][0]["attempt_id"] is None
    next_page = await evidence_page(db, learner.id, "progress", offset=1, limit=1)
    assert [item.id for item in next_page.items] == ["older"]
    assert await db.scalar(select(func.count()).select_from(CompetencyState)) == before
    assert (await client.get("/api/skills/progress/evidence?limit=101")).status_code == 422
    assert (await client.get("/api/skills/progress/evidence?offset=-1")).status_code == 422
    assert (await client.get("/api/skills/missing/evidence")).status_code == 404


async def test_hint_provenance_never_certifies_independence(
    db: AsyncSession, learner: LearnerProfile
) -> None:
    from app.db.models import Assessment, AssessmentAttempt

    db.add(SkillNode(id="hints", slug="hints", title="Hints example", domain="test"))
    db.add(LearnerProfile(id="other-hints", display_name="Other"))
    await db.flush()
    db.add(Assessment(id="question", skill_id="hints", kind="transfer", item_json={}))
    await db.flush()
    db.add_all(
        [
            AssessmentAttempt(
                id="own", learner_id=learner.id, assessment_id="question", answer="x", hint_count=0
            ),
            AssessmentAttempt(
                id="foreign",
                learner_id="other-hints",
                assessment_id="question",
                answer="private",
                hint_count=4,
            ),
        ]
    )
    await db.flush()
    db.add_all(
        [
            CompetencyEvidence(
                id="own-evidence",
                learner_id=learner.id,
                skill_id="hints",
                dimension="transfer",
                score=1,
                source_attempt_id="own",
            ),
            CompetencyEvidence(
                id="bad-reference",
                learner_id=learner.id,
                skill_id="hints",
                dimension="transfer",
                score=1,
                source_attempt_id="foreign",
            ),
        ]
    )
    await db.commit()
    result = await evidence_page(db, learner.id, "hints", offset=0, limit=20)
    items = {item.id: item for item in result.items}
    assert items["own-evidence"].reported_hint_count == 0
    assert items["own-evidence"].independence == "not_verified"
    assert items["bad-reference"].attempt_id is None
    assert items["bad-reference"].reported_hint_count is None
    empty = await evidence_page(db, learner.id, "hints", offset=20, limit=20)
    assert empty.total == 2 and empty.items == []
