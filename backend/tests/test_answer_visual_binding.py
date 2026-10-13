import copy
import hashlib
import json

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select, update

from app.db.models import Chunk, Document, DocumentVersion, LearningEvent, ModelCall, TutorAnswer
from app.kernel import answer_visual_binding as service
from app.schemas.answer_visual_binding import AnswerVisualBinding


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


async def saved(db, learner, identity="root", parent=None, sources=None):
    sources = sources or []
    snapshots = []
    if parent:
        snapshots = [
            {
                "answer_id": parent.id,
                "answer_hash": digest(parent.text),
                "question": parent.request_json["question"],
                "text": parent.text,
                "sources": parent.metadata_json["sources"],
                "source_text_hashes": parent.metadata_json["source_text_hashes"],
                "origin_status": parent.metadata_json["origin_status"],
            }
        ]
    row = TutorAnswer(
        id=identity,
        learner_id=learner.id,
        turn_id=identity,
        surface="ask",
        request_json={
            "question": f"Explain {identity}",
            "parent_answer_id": parent.id if parent else None,
        },
        text=f"Explanation of {identity}",
        fingerprint=identity,
        metadata_json={
            "parent_answer_id": parent.id if parent else None,
            "context_snapshots": snapshots,
            "context_answer_ids": [s["answer_id"] for s in snapshots],
            "context_answer_hashes": {s["answer_id"]: s["answer_hash"] for s in snapshots},
            "history_turns": len(snapshots),
            "sources": sources,
            "source_text_hashes": {s["chunk_id"]: s["text_hash"] for s in sources},
            "model": "synthetic-model",
            "prompt_version": "synthetic.v1",
            "origin_status": "unknown",
        },
    )
    if sources:
        row.request_json = {
            **row.request_json,
            "sources": {
                "passage_ids": [s["chunk_id"] for s in sources],
                "passage_hashes": {s["chunk_id"]: s["text_hash"] for s in sources},
            },
        }
    db.add(row)
    await db.commit()
    return row


async def source(db):
    db.add(Document(id="doc", title="Synthetic", source_type="manual"))
    await db.flush()
    db.add(DocumentVersion(id="v1", document_id="doc", version=1, content_hash="one"))
    await db.flush()
    db.add(Chunk(id="chunk", document_version_id="v1", ordinal=0, text="Training only"))
    await db.commit()
    return {
        "chunk_id": "chunk",
        "text": "Training only",
        "text_hash": digest("Training only"),
        "document_version_id": "v1",
    }


async def test_exact_owned_ungrounded_binding_is_not_learning_evidence(db, learner):
    row = await saved(db, learner)
    result = await service.resolve_answer_binding(
        db, learner.id, row.id, learning_purpose="Compare"
    )
    assert result.issues == () and result.grounding == "ungrounded"
    assert result.binding.question_sha256 == digest(row.request_json["question"])
    assert result.binding.answer_sha256 == digest(row.text)
    assert result.binding.learning_purpose == "Compare"
    assert (
        json.loads(result.snapshot_json)["answers"][0]["metadata_json"]["origin_status"]
        == "unknown"
    )
    assert (await service.validate_answer_binding(db, learner.id, result.binding)) == result
    assert not db.new and not db.dirty and not db.deleted
    for model in (LearningEvent, ModelCall):
        assert await db.scalar(select(func.count()).select_from(model)) == 0
    with pytest.raises(KeyError, match="Ask answer unavailable"):
        await service.resolve_answer_binding(db, "foreign", row.id)
    with pytest.raises(KeyError, match="Ask answer unavailable"):
        await service.resolve_answer_binding(db, learner.id, "absent")


@pytest.mark.parametrize(
    "field,value",
    [
        ("text", "Changed"),
        ("request_json", {"question": "New?"}),
        ("metadata_json", {}),
        ("created_at", "changed-date"),
    ],
)
async def test_target_changes_reject_old_binding(db, learner, field, value):
    row = await saved(db, learner)
    result = await service.resolve_answer_binding(db, learner.id, row.id)
    await db.execute(
        update(TutorAnswer).values(**{field: value}),
        execution_options={"synchronize_session": False},
    )
    with pytest.raises(ValueError, match="changed"):
        await service.validate_answer_binding(db, learner.id, result.binding)


async def test_full_ancestry_and_changed_historical_snapshot(db, learner):
    parent = await saved(db, learner)
    for index in range(5):
        parent = await saved(db, learner, str(index), parent)
    result = await service.resolve_answer_binding(db, learner.id, parent.id)
    assert result.issues == ()
    assert len(json.loads(result.snapshot_json)["answers"]) == 6
    await db.execute(
        update(TutorAnswer).where(TutorAnswer.id == "root").values(text="Changed"),
        execution_options={"synchronize_session": False},
    )
    current = await service.resolve_answer_binding(db, learner.id, parent.id)
    assert "changed_ancestor" in current.issues and current.grounding == "unknown"
    with pytest.raises(ValueError, match="changed"):
        await service.validate_answer_binding(db, learner.id, result.binding)


async def test_pending_edits_not_flushed_or_discarded(db, learner):
    row = await saved(db, learner)
    result = await service.resolve_answer_binding(db, learner.id, row.id)
    row.text = "Pending edit"
    assert (await service.validate_answer_binding(db, learner.id, result.binding)) == result
    assert row in db.dirty and row.text == "Pending edit"
    with db.no_autoflush:
        assert await db.scalar(select(TutorAnswer.text)) == "Explanation of root"


async def test_source_currency_and_historical_version_preserved(db, learner):
    row = await saved(db, learner, sources=[await source(db)])
    result = await service.resolve_answer_binding(db, learner.id, row.id)
    assert result.grounding == "sources_recorded"
    db.add(DocumentVersion(id="v2", document_id="doc", version=2, content_hash="two"))
    await db.commit()
    current = await service.validate_answer_binding(db, learner.id, result.binding)
    assert current.source_checks[row.id].sources[0].newer_version
    assert current.grounding == "sources_recorded"
    await db.execute(update(Chunk).values(text="Changed source"))
    current = await service.validate_answer_binding(db, learner.id, result.binding)
    assert current.source_checks[row.id].sources[0].status == "changed"
    assert current.grounding == "unknown"


@pytest.mark.parametrize("change", ["legacy", "cycle", "missing", "foreign", "malformed"])
async def test_unknown_lineage_never_claims_complete(db, learner, change):
    root = await saved(db, learner)
    child = await saved(db, learner, "child", root)
    if change == "legacy":
        root.metadata_json = {}
    elif change == "cycle":
        root.metadata_json = {**root.metadata_json, "parent_answer_id": child.id}
        root.request_json = {**root.request_json, "parent_answer_id": child.id}
    elif change == "missing":
        await db.delete(root)
    elif change == "foreign":
        from app.db.models import LearnerProfile

        other = LearnerProfile(display_name="Other")
        db.add(other)
        await db.flush()
        root.learner_id = other.id
    else:
        child.metadata_json = {
            **child.metadata_json,
            "context_snapshots": [None],
            "context_answer_ids": [{}],
        }
    await db.commit()
    result = await service.resolve_answer_binding(db, learner.id, child.id)
    assert result.issues and result.grounding == "unknown"
    if change in ("missing", "foreign"):
        assert "Explanation of root" not in json.dumps(
            [r["text"] for r in json.loads(result.snapshot_json)["answers"]]
        )  # historical child snapshot remains; foreign current record never read
    if change == "cycle":
        assert "cyclic_lineage" in result.issues


async def test_limits_and_strict_schema(db, learner, monkeypatch):
    root = await saved(db, learner)
    child = await saved(db, learner, "child", root)
    monkeypatch.setattr(service, "MAX_ANSWERS", 1)
    result = await service.resolve_answer_binding(db, learner.id, child.id)
    assert "lineage_limit" in result.issues
    data = result.binding.model_dump()
    for patch in (
        {"skill_id": "invented"},
        {"answer_sha256": "bad"},
        {"learning_purpose": "x" * 4001},
    ):
        with pytest.raises(ValidationError):
            AnswerVisualBinding.model_validate({**data, **patch})
    monkeypatch.setattr(service, "MAX_SNAPSHOT_BYTES", 1)
    with pytest.raises(ValueError, match="size limit"):
        await service.resolve_answer_binding(db, learner.id, child.id)


async def test_missing_and_inconsistent_source_snapshot(db, learner):
    passage = await source(db)
    passage = copy.deepcopy(passage)
    passage["chunk_id"] = "absent"
    row = await saved(db, learner, sources=[passage])
    result = await service.resolve_answer_binding(db, learner.id, row.id)
    assert result.source_checks[row.id].sources[0].status == "missing"
    assert result.grounding == "unknown"
    row.metadata_json = {**row.metadata_json, "sources": []}
    await db.commit()
    assert (
        "incomplete_sources"
        in (await service.resolve_answer_binding(db, learner.id, row.id)).issues
    )


async def test_source_version_move_is_not_unchanged(db, learner):
    row = await saved(db, learner, sources=[await source(db)])
    result = await service.resolve_answer_binding(db, learner.id, row.id)
    db.add(DocumentVersion(id="v2", document_id="doc", version=2, content_hash="two"))
    await db.flush()
    await db.execute(update(Chunk).values(document_version_id="v2"))
    current = await service.validate_answer_binding(db, learner.id, result.binding)
    assert current.source_checks[row.id].sources[0].status == "changed"
    assert current.grounding == "unknown"


async def test_source_request_with_lost_snapshots_is_unknown(db, learner):
    row = await saved(db, learner)
    row.request_json = {
        **row.request_json,
        "sources": {"passage_ids": ["lost"], "passage_hashes": {"lost": digest("lost text")}},
    }
    await db.commit()
    result = await service.resolve_answer_binding(db, learner.id, row.id)
    assert "incomplete_sources" in result.issues
    assert result.grounding == "unknown"


async def test_lesson_binding_is_private_read_only_and_has_separate_identity(db, learner):
    from app.db.models import Assessment, CurriculumDraft, LearningObject
    from app.kernel import answer_lesson_binding as lessons

    row = await saved(db, learner)
    result = await lessons.resolve_lesson_binding(db, learner.id, row.id)
    assert result.binding.schema_version == "answer-lesson-binding.v1"
    assert result.grounding == "ungrounded"
    assert (
        json.loads(result.snapshot_json)["answers"][0]["metadata_json"]["origin_status"]
        == "unknown"
    )
    assert await lessons.validate_lesson_binding(db, learner.id, result.binding) == result
    assert not db.new and not db.dirty and not db.deleted
    for model in (CurriculumDraft, LearningObject, Assessment, LearningEvent, ModelCall):
        assert await db.scalar(select(func.count()).select_from(model)) == 0
    for owner, identity in (("another-learner", row.id), (learner.id, "missing")):
        with pytest.raises(KeyError, match="Ask answer unavailable"):
            await lessons.resolve_lesson_binding(db, owner, identity)


async def test_lesson_binding_rejects_source_currency_change_without_answer_change(db, learner):
    from app.kernel import answer_lesson_binding as lessons

    passage = await source(db)
    row = await saved(db, learner, sources=[passage])
    original = await lessons.resolve_lesson_binding(db, learner.id, row.id)
    await db.execute(update(Chunk).where(Chunk.id == "chunk").values(text="Changed passage"))
    await db.commit()
    current = await lessons.resolve_lesson_binding(db, learner.id, row.id)
    assert current.binding.lineage_sha256 == original.binding.lineage_sha256
    assert current.binding.source_state_sha256 != original.binding.source_state_sha256
    assert current.grounding == "unknown"
    with pytest.raises(ValueError, match="source state changed"):
        await lessons.validate_lesson_binding(db, learner.id, original.binding)


async def test_lesson_binding_rejects_changed_ancestor_and_preserves_unknown(db, learner):
    from app.kernel import answer_lesson_binding as lessons

    parent = await saved(db, learner, "parent")
    row = await saved(db, learner, "child", parent=parent)
    before = await lessons.resolve_lesson_binding(db, learner.id, row.id)
    await db.execute(update(TutorAnswer).where(TutorAnswer.id == parent.id).values(text="Changed"))
    await db.commit()
    with pytest.raises(ValueError, match="lineage"):
        await lessons.validate_lesson_binding(db, learner.id, before.binding)
    current = await lessons.resolve_lesson_binding(db, learner.id, row.id)
    assert "changed_ancestor" in current.issues
    assert current.grounding == "unknown"
