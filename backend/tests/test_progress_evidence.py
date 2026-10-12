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


async def test_saved_assessment_link_is_owned_and_does_not_duplicate_evidence(client, db):
    from app.db.models import TutorAnswer
    from tests.test_assessment_revisions import original

    root, _ = await original(client, db)
    saved = await db.scalar(
        select(TutorAnswer).where(TutorAnswer.turn_id == f"assessment:{root.id}")
    )
    skill_id = saved.metadata_json["skill_id"]
    page = await evidence_page(db, root.learner_id, skill_id, offset=0, limit=20)
    assert len(page.items) == page.total == 1
    assert page.items[0].answer_id == saved.id
    other = LearnerProfile(display_name="Other")
    db.add(other)
    await db.flush()
    saved.learner_id = other.id
    await db.commit()
    hidden = await evidence_page(db, root.learner_id, skill_id, offset=0, limit=20)
    assert hidden.total == 1
    assert hidden.items[0].answer_id is None


async def test_task_context_preserves_historical_facts_and_rejects_inconsistent_snapshot(client, db):
    from app.db.models import Assessment
    from tests.test_assessment_revisions import original

    root, _ = await original(client, db)
    assessment = await db.get(Assessment, root.assessment_id)
    page = await evidence_page(db, root.learner_id, assessment.skill_id, offset=0, limit=20)
    context = page.items[0].task_context
    assert context is not None
    assert context.task_kind == assessment.kind
    assert context.reported_hint_count == root.hint_count
    assert context.independence == "not_verified"
    assert context.assistance_coverage == "partial"
    assert not context.revised_work
    # Current task edits cannot rewrite the historical snapshot.
    assessment.kind = "changed"
    await db.commit()
    page = await evidence_page(db, root.learner_id, assessment.skill_id, offset=0, limit=20)
    assert page.items[0].task_context == context
    root.hint_count += 1
    await db.commit()
    page = await evidence_page(db, root.learner_id, assessment.skill_id, offset=0, limit=20)
    assert page.items[0].task_context is None


def test_task_context_rejects_missing_future_malformed_and_conflicting_metadata():
    from copy import deepcopy

    from app.db.models import AssessmentAttempt
    from app.kernel.progress import task_context
    from app.schemas.assessment_provenance import AssessmentProvenance

    facts = AssessmentProvenance(
        task_kind="mcq", content_fingerprint="fingerprint", rubric_version=None,
        grading_method="deterministic", reported_hint_count=-1, revision_of_attempt_id=None,
    ).model_dump()
    attempt = AssessmentAttempt(
        content_fingerprint="fingerprint", grader_route="deterministic", hint_count=-1,
        revision_of_attempt_id=None,
    )
    def project(value):
        attempt.deterministic_result_json = {"evidence_provenance": value}
        return task_context(attempt)

    assert project(facts).reported_hint_count == -1
    for field in facts:
        missing = deepcopy(facts)
        del missing[field]
        assert project(missing) is None
    for field, value in (
        ("schema_version", 2), ("independence", "verified"),
        ("qualification", "passed"), ("reported_hint_count", "-1"),
        ("content_fingerprint", "different"), ("revision_of_attempt_id", "other"),
        ("grading_method", "hosted"), ("task_kind", " "),
    ):
        assert project({**facts, field: value}) is None
    for malformed in (None, [], "invalid"):
        assert project(malformed) is None
    attempt.llm_result_json = {"evidence_provenance": facts}
    assert project(facts) is None
    assert task_context(None) is None


async def test_cross_skill_attempt_reference_does_not_disclose_context(client, db):
    from app.db.models import Assessment
    from tests.test_assessment_revisions import original

    root, _ = await original(client, db)
    assessment = await db.get(Assessment, root.assessment_id)
    original_skill = assessment.skill_id
    db.add(SkillNode(id="different-skill", slug="different-skill", title="Other", domain="test"))
    await db.flush()
    assessment.skill_id = "different-skill"
    await db.commit()
    page = await evidence_page(db, root.learner_id, original_skill, offset=0, limit=20)
    assert page.total == 1
    assert page.items[0].attempt_id is None
    assert page.items[0].answer_id is None
    assert page.items[0].task_context is None
