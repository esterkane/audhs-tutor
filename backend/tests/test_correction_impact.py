from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.errors import AppError
from app.db import models
from app.kernel import correction_drafts as drafts
from app.kernel import correction_impact
from app.schemas.correction_drafts import CreateCorrectionDraft
from tests.test_correction_validation import sourced_question


async def test_impact_is_owned_read_only_and_counts_exact_targets(db, learner, client):
    q, chunk, _ = await sourced_question(db)
    result = await drafts.create(
        db,
        learner.id,
        CreateCorrectionDraft(request_id=uuid4(), assessment_id=q.id, expected_question_revision=0),
    )
    other = models.LearnerProfile(display_name="Other")
    db.add(other)
    await db.flush()
    for owner, active, kind in [
        (learner.id, True, "mcq"),
        (learner.id, False, "mcq"),
        (learner.id, True, "vocab"),
        (other.id, True, "mcq"),
    ]:
        db.add(
            models.ReviewItem(
                learner_id=owner,
                skill_id=q.skill_id,
                item_type=kind,
                active=active,
                prompt_json={"ref": q.id, "type": kind},
            )
        )
    for owner in [None, learner.id, other.id]:
        db.add(
            models.Assessment(
                skill_id=q.skill_id,
                kind="code",
                owner_learner_id=owner,
                item_json={"check_assessment_id": q.id},
            )
        )
    await db.commit()
    first = await correction_impact.preview(db, learner.id, result.draft_id)
    assert first.affected_reviews == 1 and first.linked_exercises == 2
    assert first.passages[0].text == chunk.text and not first.passages[0].truncated
    assert first.review.source_status == "unchanged" and not first.publication_available
    assert (
        await correction_impact.preview(db, learner.id, result.draft_id)
    ).preview_token == first.preview_token
    with pytest.raises(AppError) as error:
        await correction_impact.preview(db, other.id, result.draft_id)
    assert error.value.http_status == 404
    response = await client.get(f"/api/questions/correction-drafts/{result.draft_id}/impact")
    assert response.status_code == 200, response.text
    assert response.json()["affected_reviews"] == 1
    for model in [models.QuestionState, models.AssessmentAttempt, models.CompetencyEvidence]:
        assert await db.scalar(select(func.count()).select_from(model)) == 0


async def test_preview_identity_changes_with_review_impact_and_source_content(db, learner):
    q, chunk, _ = await sourced_question(db)
    result = await drafts.create(
        db,
        learner.id,
        CreateCorrectionDraft(request_id=uuid4(), assessment_id=q.id, expected_question_revision=0),
    )
    await db.commit()
    first = await correction_impact.preview(db, learner.id, result.draft_id)
    db.add(
        models.ReviewItem(
            learner_id=learner.id,
            skill_id=q.skill_id,
            item_type="mcq",
            prompt_json={"assessment_id": q.id},
        )
    )
    await db.commit()
    second = await correction_impact.preview(db, learner.id, result.draft_id)
    assert second.preview_token != first.preview_token
    chunk.text = "X" * 6001
    await db.commit()
    third = await correction_impact.preview(db, learner.id, result.draft_id)
    assert third.preview_token != second.preview_token
    assert third.review.source_status == "changed"
    assert len(third.passages[0].text) == 6000 and third.passages[0].truncated
    q.item_json = {**q.item_json, "source_chunk_id": "missing"}
    await db.commit()
    missing = await correction_impact.preview(db, learner.id, result.draft_id)
    assert missing.passages[0].text is None and missing.passages[0].status == "unresolved"
