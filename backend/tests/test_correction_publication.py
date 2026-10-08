import copy
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.errors import AppError
from app.db import models
from app.kernel import correction_drafts as drafts
from app.kernel import (
    correction_impact,
    correction_publication,
    question_replacements,
    question_state,
)
from app.schemas.correction_drafts import (
    CreateCorrectionDraft,
    PublishCorrectionDraft,
    SaveCorrectionDraft,
)
from tests.test_correction_validation import sourced_question


async def prepared(db, learner, with_rubric=False):
    q, chunk, _ = await sourced_question(db)
    if with_rubric:
        rubric = models.AssessmentRubric(
            criteria_json=[{"criterion": "Explain the cause", "keywords": []}]
        )
        db.add(rubric)
        await db.flush()
        q.kind = "explain_back"
        q.item_json = {"prompt": "Explain the cause.", "source_chunk_id": chunk.id}
        q.rubric_id = rubric.id
        await db.commit()
    created = await drafts.create(
        db,
        learner.id,
        CreateCorrectionDraft(
            request_id=uuid4(),
            assessment_id=q.id,
            expected_question_revision=0,
        ),
    )
    candidate = {"item": {**q.item_json, "question": "Which corrected option?"}, "rubric": None}
    if with_rubric:
        candidate = {
            "item": {**q.item_json, "prompt": "Explain cause and effect."},
            "rubric": [{"criterion": "Explain cause and effect", "keywords": []}],
        }
    saved = await drafts.change(
        db,
        learner.id,
        created.draft_id,
        SaveCorrectionDraft(
            request_id=uuid4(),
            expected_revision=1,
            candidate=candidate,
        ),
    )
    await db.commit()
    preview = await correction_impact.preview(db, learner.id, saved.draft_id)
    body = PublishCorrectionDraft(
        request_id=uuid4(),
        expected_revision=saved.revision,
        preview_token=preview.preview_token,
        reviewed_sources=True,
    )
    return q, chunk, saved.draft_id, body


async def test_publish_owned_future_only_and_replay(db, learner):
    q, chunk, draft_id, body = await prepared(db, learner)
    original = copy.deepcopy(q.item_json)
    result = await correction_publication.publish(db, learner.id, draft_id, body)
    await db.commit()
    assert result.status == "published" and result.revision == 3
    new = await question_replacements.resolve(db, learner.id, q.id)
    assert new.id == result.replacement_id and new.owner_learner_id == learner.id
    assert q.item_json == original and new.item_json["question"] == "Which corrected option?"
    assert (await question_state.read(db, learner.id, q.id)).state == "superseded"
    other = models.LearnerProfile(display_name="Other")
    db.add(other)
    await db.commit()
    assert (await question_replacements.resolve(db, other.id, q.id)).id == q.id
    with pytest.raises(AppError):
        await question_state.require_visible(db, other.id, new.id)
    chunk.text = "Later source version"
    await db.commit()
    assert await correction_publication.publish(db, learner.id, draft_id, body) == result
    changed = body.model_copy(update={"expected_revision": 3})
    with pytest.raises(AppError, match="already used"):
        await correction_publication.publish(db, learner.id, draft_id, changed)
    for model in [
        models.AssessmentAttempt,
        models.CompetencyEvidence,
        models.MemoryState,
        models.ReviewItem,
    ]:
        assert await db.scalar(select(func.count()).select_from(model)) == 0


@pytest.mark.parametrize("change", ["source", "candidate", "review", "state"])
async def test_rechecks_preview_before_writes(db, learner, change):
    q, chunk, draft_id, body = await prepared(db, learner)
    if change == "source":
        chunk.text = "Different source"
    elif change == "candidate":
        row = await drafts.get(db, learner.id, draft_id)
        row.candidate_json = {
            **row.candidate_json,
            "item": {**q.item_json, "question": "New wording"},
        }
    elif change == "review":
        db.add(
            models.ReviewItem(
                learner_id=learner.id,
                skill_id=q.skill_id,
                item_type="mcq",
                prompt_json={"ref": q.id},
            )
        )
    else:
        db.add(
            models.QuestionState(
                learner_id=learner.id,
                assessment_id=q.id,
                state="suspended",
                revision=1,
                reason="Reported",
                updated_at="now",
            )
        )
    await db.commit()
    with pytest.raises(AppError) as error:
        await correction_publication.publish(db, learner.id, draft_id, body)
    assert error.value.code == "correction_preview_conflict"
    assert await db.scalar(select(func.count()).select_from(models.QuestionReplacement)) == 0


@pytest.mark.parametrize("boundary", [1, 2, 3, 4])
async def test_rollback_at_each_flush(db, learner, monkeypatch, boundary):
    q, _, draft_id, body = await prepared(db, learner, with_rubric=True)
    learner_id, qid = learner.id, q.id
    real_flush = db.flush
    calls = 0

    async def failing_flush(*args, **kwargs):
        nonlocal calls
        await real_flush(*args, **kwargs)
        calls += 1
        if calls == boundary:
            raise RuntimeError("injected write failure")

    monkeypatch.setattr(db, "flush", failing_flush)
    with pytest.raises(RuntimeError, match="injected"):
        await correction_publication.publish(db, learner_id, draft_id, body)
    await db.rollback()
    monkeypatch.setattr(db, "flush", real_flush)
    assert (await drafts.get(db, learner_id, draft_id)).status == "draft"
    assert await db.scalar(select(func.count()).select_from(models.Assessment)) == 1
    assert await db.scalar(select(func.count()).select_from(models.AssessmentRubric)) == 1
    assert await db.get(models.QuestionReplacement, (learner_id, qid)) is None
    assert await db.get(models.QuestionState, (learner_id, qid)) is None
    assert (
        await db.get(models.QuestionCorrectionCommand, (learner_id, str(body.request_id))) is None
    )


async def test_stale_second_publication_conflicts(db, learner):
    _, _, draft_id, body = await prepared(db, learner)
    await correction_publication.publish(db, learner.id, draft_id, body)
    await db.commit()
    with pytest.raises(AppError) as error:
        await correction_publication.publish(
            db, learner.id, draft_id, body.model_copy(update={"request_id": uuid4()})
        )
    assert error.value.code == "correction_draft_conflict"
    assert await db.scalar(select(func.count()).select_from(models.QuestionReplacement)) == 1


@pytest.mark.parametrize("same_request", [False, True])
async def test_concurrent_publish_serializes(db, learner, session_factory, same_request):
    import asyncio

    _, _, draft_id, body = await prepared(db, learner)
    learner_id = learner.id
    await db.rollback()

    async def run(command):
        async with session_factory() as connection:
            try:
                result = await correction_publication.publish(
                    connection, learner_id, draft_id, command
                )
                await connection.commit()
                return result
            except AppError as error:
                await connection.rollback()
                return error.code

    second = body if same_request else body.model_copy(update={"request_id": uuid4()})
    results = await asyncio.gather(run(body), run(second))
    if same_request:
        assert results[0] == results[1] and not isinstance(results[0], str)
    else:
        assert sum(value == "correction_draft_conflict" for value in results) == 1
    assert await db.scalar(select(func.count()).select_from(models.QuestionReplacement)) == 1


async def test_suspended_original_and_chained_replacement(db, learner):
    q, _, draft_id, _ = await prepared(db, learner)
    state = models.QuestionState(
        learner_id=learner.id,
        assessment_id=q.id,
        state="suspended",
        revision=1,
        reason="bad",
        updated_at="now",
    )
    db.add(state)
    await db.commit()
    # Create the proposal against the deliberately suspended revision, not a stale one.
    first = await drafts.create(
        db,
        learner.id,
        CreateCorrectionDraft(
            request_id=uuid4(),
            assessment_id=q.id,
            expected_question_revision=1,
        ),
    )
    result = None
    for expected_original, draft_id in [(q.id, first.draft_id), (None, None)]:
        if draft_id is None:
            assert result is not None
            expected_original = result.replacement_id
            created = await drafts.create(
                db,
                learner.id,
                CreateCorrectionDraft(
                    request_id=uuid4(),
                    assessment_id=expected_original,
                    expected_question_revision=0,
                ),
            )
            draft_id = created.draft_id
        draft = await drafts.get(db, learner.id, draft_id)
        candidate = copy.deepcopy(draft.candidate_json)
        candidate["item"]["question"] += " Corrected."
        await drafts.change(
            db,
            learner.id,
            draft_id,
            SaveCorrectionDraft(
                request_id=uuid4(),
                expected_revision=1,
                candidate=candidate,
            ),
        )
        await db.commit()
        preview = await correction_impact.preview(db, learner.id, draft_id)
        result = await correction_publication.publish(
            db,
            learner.id,
            draft_id,
            PublishCorrectionDraft(
                request_id=uuid4(),
                expected_revision=2,
                preview_token=preview.preview_token,
                reviewed_sources=True,
            ),
        )
        await db.commit()
        assert (
            await question_replacements.resolve(db, learner.id, q.id)
        ).id == result.replacement_id
        assert (await question_state.read(db, learner.id, expected_original)).state == "superseded"


@pytest.mark.parametrize("withdraw", [False, True])
async def test_report_resolution_is_atomic_and_keeps_history(db, learner, withdraw):
    from app.kernel import question_corrections

    q, _, draft_id, _ = await prepared(db, learner)
    report = models.QuestionFeedback(
        learner_id=learner.id,
        target_key="synthetic-report",
        assessment_id=q.id,
        verdict="bad",
        labels_json=[],
        note="Needs correction",
        snapshot_json={"kind": q.kind, "item": copy.deepcopy(q.item_json), "skill_id": q.skill_id},
    )
    db.add(report)
    await db.flush()
    draft = await drafts.get(db, learner.id, draft_id)
    draft.feedback_id = report.id
    if withdraw:
        report.withdrawn_at = "now"
    await db.commit()
    preview = await correction_impact.preview(db, learner.id, draft_id)
    body = PublishCorrectionDraft(
        request_id=uuid4(),
        expected_revision=2,
        preview_token=preview.preview_token,
        reviewed_sources=True,
    )
    if withdraw:
        with pytest.raises(AppError) as error:
            await correction_publication.publish(db, learner.id, draft_id, body)
        assert error.value.code == "correction_report_conflict"
        assert (await drafts.get(db, learner.id, draft_id)).status == "draft"
    else:
        assert (await question_corrections.inbox(db, learner.id, 0, 20)).total == 1
        await correction_publication.publish(db, learner.id, draft_id, body)
        await db.commit()
        assert (await question_corrections.inbox(db, learner.id, 0, 20)).total == 0
        kept = await db.get(models.QuestionFeedback, report.id)
        assert kept.note == "Needs correction" and kept.withdrawn_at is None


async def test_publication_endpoint_confirm_recover_and_stale_retry(db, learner, client):
    _, _, draft_id, body = await prepared(db, learner)
    preview = (await client.get(f"/api/questions/correction-drafts/{draft_id}/impact")).json()
    assert preview["publication_available"] and not preview["publication_blockers"]
    path = f"/api/questions/correction-drafts/{draft_id}/publish"
    payload = body.model_dump(mode="json")
    assert (await client.post(path, json={**payload, "reviewed_sources": False})).status_code == 422
    response = await client.post(path, json=payload)
    assert response.status_code == 200, response.text
    receipt = response.json()
    assert receipt["status"] == "published" and receipt["replacement_id"]
    assert (
        await client.get(f"/api/questions/correction-commands/{body.request_id}")
    ).json() == receipt
    assert (await client.post(path, json=payload)).json() == receipt
    assert (
        await client.post(path, json={**payload, "request_id": str(uuid4())})
    ).status_code == 409
    view = (await client.get(f"/api/questions/correction-drafts/{draft_id}")).json()
    assert view["status"] == "published"


@pytest.mark.parametrize("blocked", ["missing_source", "listening", "code"])
async def test_endpoint_blocks_unverified_content(db, learner, client, blocked):
    q, _, _ = await sourced_question(db)
    if blocked == "missing_source":
        q.item_json = {key: value for key, value in q.item_json.items() if key != "source_chunk_id"}
    elif blocked == "listening":
        q.item_json = {**q.item_json, "listening": {"chunk_id": q.item_json["source_chunk_id"]}}
    else:
        q.kind = "code"
    await db.commit()
    draft = await drafts.create(
        db,
        learner.id,
        CreateCorrectionDraft(
            request_id=uuid4(),
            assessment_id=q.id,
            expected_question_revision=0,
        ),
    )
    await drafts.change(
        db,
        learner.id,
        draft.draft_id,
        SaveCorrectionDraft(
            request_id=uuid4(),
            expected_revision=1,
            candidate={"item": {**q.item_json, "question": "Corrected question?"}, "rubric": None},
        ),
    )
    await db.commit()
    path = f"/api/questions/correction-drafts/{draft.draft_id}"
    preview = (await client.get(path + "/impact")).json()
    assert not preview["publication_available"] and preview["publication_blockers"]
    response = await client.post(
        path + "/publish",
        json={
            "request_id": str(uuid4()),
            "expected_revision": 2,
            "preview_token": preview["preview_token"],
            "reviewed_sources": True,
        },
    )
    assert response.status_code == 409, response.text
    assert await db.scalar(select(func.count()).select_from(models.QuestionReplacement)) == 0
