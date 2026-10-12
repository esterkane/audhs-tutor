import hashlib
import json

import pytest
from sqlalchemy import delete, select, update

from app.db.models import Chunk, Document, DocumentVersion, LearningObject, SkillNode
from app.kernel.visual_binding import validate_stored_binding
from app.schemas.visual_binding import VisualBinding


async def seed(db):
    db.add(SkillNode(id="skill", domain="ai_ml", slug="synthetic-visual", title="Synthetic"))
    db.add(Document(id="doc", title="Synthetic reference", source_type="manual"))
    await db.flush()
    db.add(DocumentVersion(id="version", document_id="doc", content_hash="synthetic", version=1))
    await db.flush()
    text = "Fit on training data only."
    db.add(Chunk(id="chunk", document_version_id="version", ordinal=0, text=text))
    db.add(
        LearningObject(
            id="object",
            concept="Leakage",
            version=1,
            skill_id="skill",
            goal="Explain leakage",
            success_criteria_json=["Distinguish fit and transform"],
            sources_json=["chunk"],
        )
    )
    await db.commit()
    binding = VisualBinding.model_validate_json(
        json.dumps(
            {
                "schema_version": "visual-binding.v1",
                "object_id": "object",
                "object_version": 1,
                "skill_id": "skill",
                "goal": "Explain leakage",
                "criteria": [{"index": 0, "text": "Distinguish fit and transform"}],
                "sources": [
                    {
                        "chunk_id": "chunk",
                        "document_version_id": "version",
                        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                    }
                ],
            }
        )
    )
    return binding


async def test_checks_exact_historical_object_without_substituting_latest(db):
    binding = await seed(db)
    db.add(
        LearningObject(
            id="new-object",
            concept="Updated leakage",
            version=2,
            skill_id="skill",
            goal="New objective",
            success_criteria_json=[],
            sources_json=[],
        )
    )
    await db.commit()
    await validate_stored_binding(db, binding)
    assert not db.new and not db.dirty and not db.deleted


@pytest.mark.parametrize("change", ["missing_object", "wrong_version", "text", "source_membership"])
async def test_rejects_missing_or_changed_persisted_evidence(db, change):
    binding = await seed(db)
    if change == "missing_object":
        await db.execute(delete(LearningObject))
    elif change == "wrong_version":
        await db.execute(update(LearningObject).values(version=2))
    elif change == "text":
        await db.execute(update(Chunk).values(text="Changed source"))
    else:
        await db.execute(update(LearningObject).values(sources_json=[]))
    await db.commit()
    with pytest.raises(ValueError):
        await validate_stored_binding(db, binding)


async def test_pending_edits_are_neither_flushed_nor_discarded(db):
    binding = await seed(db)
    obj = await db.get(LearningObject, "object")
    chunk = await db.get(Chunk, "chunk")
    obj.goal = "Uncommitted edit"
    chunk.text = "Uncommitted source edit"
    await validate_stored_binding(db, binding)
    assert obj.goal == "Uncommitted edit" and chunk.text == "Uncommitted source edit"
    assert obj in db.dirty and chunk in db.dirty
    with db.no_autoflush:
        assert await db.scalar(select(LearningObject.goal)) == "Explain leakage"


async def test_stale_identity_map_cannot_pass_changed_stored_source(db):
    binding = await seed(db)
    chunk = await db.get(Chunk, "chunk")
    await db.execute(
        update(Chunk).values(text="Changed persisted text"),
        execution_options={"synchronize_session": False},
    )
    assert chunk.text == "Fit on training data only."
    with pytest.raises(ValueError, match="source text changed"):
        await validate_stored_binding(db, binding)
