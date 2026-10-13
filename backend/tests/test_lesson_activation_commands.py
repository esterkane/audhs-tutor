import asyncio
import copy

import pytest
from sqlalchemy import event, func, select, update

from app.core.errors import AppError
from app.db.models import (
    Assessment,
    AssessmentAttempt,
    AssessmentTaskReview,
    CompetencyEvidence,
    CurriculumDraft,
    LearnerProfile,
    LearningObject,
    LessonActivation,
    LessonActivationAssessment,
    LessonActivationEdge,
    LessonActivationObject,
    LessonActivationSkill,
    MemoryState,
    ModelCall,
    SkillEdge,
    SkillNode,
    TutorAnswer,
)
from app.kernel import curriculum
from app.kernel.lesson_activation import LessonActivationRepository, payload_digest
from app.kernel.lesson_promotion import LessonPromotionRepository
from tests.test_lesson_promotion_commands import body, raw


async def prepared(db, learner, factory):
    promotion = await LessonPromotionRepository(factory).create(
        learner.id, "draft-key", raw(await body(db, learner))
    )
    async with factory() as check:
        draft = await check.get(CurriculumDraft, promotion.draft_id)
        command = {
            "promotion_id": promotion.promotion_id,
            "expected_version": draft.version,
            "payload_sha256": payload_digest(draft.payload_json),
        }
    return promotion, command


async def test_activate_retry_after_changed_source_and_no_learning_evidence(
    db, learner, session_factory
):
    promotion, command = await prepared(db, learner, session_factory)
    repo = LessonActivationRepository(session_factory)
    a, b = await asyncio.gather(*[repo.activate(learner.id, "key", raw(command)) for _ in range(2)])
    assert a == b and len(a.skill_ids) == len(a.object_ids) == len(a.assessment_ids) == 1
    assert await repo.get(learner.id, a.activation_id) == a
    for identity in ("other", "missing"):
        with pytest.raises(AppError) as denied:
            await repo.get(identity, a.activation_id)
        assert denied.value.http_status == 404
    async with session_factory() as check:
        draft = await check.get(CurriculumDraft, promotion.draft_id)
        assert draft.status == "published" and draft.version == 2
        node = await check.get(SkillNode, a.skill_ids[0])
        assert node.owner_learner_id == learner.id and node.area_id is None
        assessment = await check.get(Assessment, a.assessment_ids[0])
        assert assessment.owner_learner_id == learner.id
        for model in (
            AssessmentAttempt,
            AssessmentTaskReview,
            CompetencyEvidence,
            MemoryState,
            ModelCall,
        ):
            assert await check.scalar(select(func.count()).select_from(model)) == 0
        await check.execute(
            update(TutorAnswer).where(TutorAnswer.id == "root").values(text="Changed")
        )
        await check.commit()
    assert await repo.activate(learner.id, "key", raw(command)) == a
    with pytest.raises(AppError, match="different content"):
        await repo.activate(learner.id, "key", raw({**command, "expected_version": 2}))
    with pytest.raises(AppError, match="another request"):
        await repo.activate(learner.id, "new-key", raw(command))


@pytest.mark.parametrize("mutation", ["version", "payload", "answer", "rejected", "foreign"])
async def test_stale_and_foreign_leave_no_writes(db, learner, session_factory, mutation):
    promotion, command = await prepared(db, learner, session_factory)
    async with session_factory() as check:
        draft = await check.get(CurriculumDraft, promotion.draft_id)
        if mutation == "version":
            draft.version += 1
        elif mutation == "payload":
            draft.payload_json = {**draft.payload_json, "area_title": "Changed"}
        elif mutation == "answer":
            await check.execute(update(TutorAnswer).values(text="Changed"))
        elif mutation == "rejected":
            draft.status = "rejected"
        await check.commit()
    with pytest.raises(AppError):
        await LessonActivationRepository(session_factory).activate(
            "foreign" if mutation == "foreign" else learner.id, "key", raw(command)
        )
    async with session_factory() as check:
        for model in (LessonActivation, SkillNode, LearningObject, Assessment):
            assert await check.scalar(select(func.count()).select_from(model)) == 0


async def test_multi_entity_private_prerequisites_and_shared_unchanged(
    db, learner, session_factory
):
    promotion, command = await prepared(db, learner, session_factory)
    async with session_factory() as check:
        for name, owner in [("shared", None), ("own", learner.id)]:
            check.add(
                SkillNode(id=name, slug=name, title=name, domain="ai_ml", owner_learner_id=owner)
            )
        draft = await check.get(CurriculumDraft, promotion.draft_id)
        payload = copy.deepcopy(draft.payload_json)
        first = payload["skills"][0]["slug"]
        payload["skills"][0]["prerequisites"] = ["shared", "own"]
        payload["skills"].append(
            {**payload["skills"][0], "slug": "second", "prerequisites": [first]}
        )
        payload["learning_objects"].append({**payload["learning_objects"][0], "skill": "second"})
        payload["assessments"].append({**payload["assessments"][0], "skill": "second"})
        draft.payload_json = payload
        await check.commit()
        # Shared validation remains shared-only, even for the current learner's prerequisite.
        assert any(
            p.level == "error" and "own" in p.message
            for p in await curriculum.validate_payload(check, payload)
        )
        command["payload_sha256"] = payload_digest(payload)
    receipt = await LessonActivationRepository(session_factory).activate(
        learner.id, "key", raw(command)
    )
    assert len(receipt.skill_ids) == len(receipt.object_ids) == len(receipt.assessment_ids) == 2
    assert len(receipt.edge_ids) == 3
    async with session_factory() as check:
        assert (await check.get(SkillNode, "shared")).title == "shared"
        assert (await check.get(SkillNode, "own")).title == "own"
        for model, count in [
            (LessonActivationSkill, 2),
            (LessonActivationObject, 2),
            (LessonActivationAssessment, 2),
            (LessonActivationEdge, 3),
        ]:
            assert await check.scalar(select(func.count()).select_from(model)) == count


async def test_late_storage_failure_rolls_back_all_and_can_retry(db, learner, session_factory):
    promotion, command = await prepared(db, learner, session_factory)

    def fail(*args):
        raise RuntimeError("synthetic late failure")

    event.listen(LessonActivationAssessment, "before_insert", fail)
    repo = LessonActivationRepository(session_factory)
    try:
        with pytest.raises(RuntimeError, match="late failure"):
            await repo.activate(learner.id, "key", raw(command))
    finally:
        event.remove(LessonActivationAssessment, "before_insert", fail)
    async with session_factory() as check:
        for model in (LessonActivation, SkillNode, LearningObject, Assessment, SkillEdge):
            assert await check.scalar(select(func.count()).select_from(model)) == 0
        draft = await check.get(CurriculumDraft, promotion.draft_id)
        assert draft.status == "draft" and draft.version == 1
    assert (await repo.activate(learner.id, "key", raw(command))).activated_version == 1


async def test_different_keys_race_creates_one_activation(db, learner, session_factory):
    _, command = await prepared(db, learner, session_factory)
    repo = LessonActivationRepository(session_factory)
    results = await asyncio.gather(
        *[repo.activate(learner.id, k, raw(command)) for k in ["a", "b"]], return_exceptions=True
    )
    assert sum(isinstance(r, AppError) for r in results) == 1
    async with session_factory() as check:
        assert await check.scalar(select(func.count()).select_from(LessonActivation)) == 1


@pytest.mark.parametrize(
    "invalid", ["foreign_prerequisite", "duplicate_object", "cycle", "orphan", "missing_source"]
)
async def test_invalid_curriculum_is_atomic(db, learner, session_factory, invalid):
    promotion, command = await prepared(db, learner, session_factory)
    async with session_factory() as check:
        check.add(LearnerProfile(id="other", display_name="Other"))
        await check.flush()
        check.add(
            SkillNode(
                id="foreign",
                slug="foreign",
                title="Foreign",
                domain="ai_ml",
                owner_learner_id="other",
            )
        )
        draft = await check.get(CurriculumDraft, promotion.draft_id)
        payload = copy.deepcopy(draft.payload_json)
        if invalid == "foreign_prerequisite":
            payload["skills"][0]["prerequisites"] = ["foreign"]
        elif invalid == "duplicate_object":
            payload["learning_objects"] *= 2
        elif invalid == "missing_source":
            payload["assessments"][0]["source_chunk_id"] = "missing"
        elif invalid == "cycle":
            payload["skills"][0]["prerequisites"] = [payload["skills"][0]["slug"]]
        else:
            payload["assessments"][0]["skill"] = "missing"
        draft.payload_json = payload
        await check.commit()
        command["payload_sha256"] = payload_digest(payload)
    with pytest.raises(ValueError):
        await LessonActivationRepository(session_factory).activate(learner.id, "key", raw(command))
    async with session_factory() as check:
        assert await check.scalar(select(func.count()).select_from(LessonActivation)) == 0
        assert await check.scalar(select(func.count()).select_from(SkillNode)) == 1


async def test_changed_passage_conflicts_without_changing_answer_or_draft(
    db, learner, session_factory
):
    from app.db.models import Chunk
    from app.kernel.answer_lesson_binding import resolve_lesson_binding
    from tests.test_answer_visual_binding import saved, source

    content = await body(db, learner)
    passage = await source(db)
    answer = await saved(db, learner, identity="sourced", sources=[passage])
    resolved = await resolve_lesson_binding(db, learner.id, answer.id)
    content["binding"] = resolved.binding.model_dump(mode="json")
    await db.commit()
    promotion = await LessonPromotionRepository(session_factory).create(
        learner.id, "sourced", raw(content)
    )
    async with session_factory() as check:
        draft = await check.get(CurriculumDraft, promotion.draft_id)
        before = copy.deepcopy(draft.payload_json)
        command = {
            "promotion_id": promotion.promotion_id,
            "expected_version": 1,
            "payload_sha256": payload_digest(before),
        }
        await check.execute(update(Chunk).where(Chunk.id == "chunk").values(text="Updated source"))
        await check.commit()
    with pytest.raises(AppError, match="source history changed"):
        await LessonActivationRepository(session_factory).activate(learner.id, "key", raw(command))
    async with session_factory() as check:
        draft = await check.get(CurriculumDraft, promotion.draft_id)
        assert draft.status == "draft" and draft.version == 1 and draft.payload_json == before
        assert (await check.get(TutorAnswer, answer.id)).text == answer.text
        for model in (LessonActivation, SkillNode, Assessment, LearningObject):
            assert await check.scalar(select(func.count()).select_from(model)) == 0


async def test_receipt_read_is_consistent_during_deletion(
    db, learner, session_factory, monkeypatch
):
    from sqlalchemy import delete

    from app.kernel import lesson_activation as service

    _, command = await prepared(db, learner, session_factory)
    repo = LessonActivationRepository(session_factory)
    receipt = await repo.activate(learner.id, "key", raw(command))
    original = service._receipt

    async def remove_then_read(reader, row):
        async with session_factory() as writer:
            for model in (
                LessonActivationObject,
                LessonActivationAssessment,
                LessonActivationEdge,
                LessonActivationSkill,
                LessonActivation,
            ):
                await writer.execute(delete(model).where(model.learner_id == learner.id))
            await writer.commit()
        return await original(reader, row)

    monkeypatch.setattr(service, "_receipt", remove_then_read)
    assert await repo.get(learner.id, receipt.activation_id) == receipt
    with pytest.raises(AppError) as missing:
        await repo.get(learner.id, receipt.activation_id)
    assert missing.value.http_status == 404
