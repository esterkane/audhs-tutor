import asyncio
import json

import pytest
from pydantic import ValidationError
from sqlalchemy import delete, func, select, update

from app.core.errors import AppError
from app.db.models import (
    AuthoredVisualDocument as Document,
)
from app.db.models import (
    AuthoredVisualOperation as Operation,
)
from app.db.models import (
    AuthoredVisualReview as Review,
)
from app.db.models import (
    AuthoredVisualSourceSnapshot as Snapshot,
)
from app.db.models import (
    AuthoredVisualVersion as Version,
)
from app.db.models import (
    Chunk,
    ChunkProvenance,
    LearnerProfile,
    LearningEvent,
    ModelCall,
    TutorAnswer,
)
from app.kernel.answer_visual_binding import resolve_answer_binding
from app.kernel.authored_visuals import VisualRepository
from app.schemas.authored_visuals import VisualOrigin, parse_command
from tests.test_answer_visual_binding import saved, source
from tests.test_visual_binding_database import seed as lesson_seed


def raw(command):
    return json.dumps(command).encode()


async def ask_spec(db, learner, sourced=False):
    sources = [await source(db)] if sourced else []
    answer = await saved(db, learner, sources=sources)
    if sourced:
        db.add(
            ChunkProvenance(
                chunk_id="chunk",
                source_id="synthetic",
                path="local",
                source_type="manual",
                trust_tier=2,
            )
        )
        await db.commit()
    binding = (await resolve_answer_binding(db, learner.id, answer.id)).binding
    return {
        "schema_version": "visual.answer.v1",
        "kind": "relationship",
        "binding": binding.model_dump(mode="json"),
        "title": "Train then predict",
        "text_equivalent": "Fit a model, then use it for prediction.",
        "directed": True,
        "source_chunk_ids": [s["chunk_id"] for s in sources],
        "nodes": [
            {"id": "fit", "label": "Fit", "explanation": "Learn from training examples."},
            {"id": "predict", "label": "Predict", "explanation": "Use learned parameters."},
        ],
        "edges": [{"id": "next", "source": "fit", "target": "predict", "label": "then"}],
    }


def save_command(spec, receipt=None):
    return {
        "action": "save",
        "document_id": receipt.document_id if receipt else None,
        "expected_revision": receipt.revision if receipt else 0,
        "spec": spec,
    }


def review_command(receipt, decision="accept"):
    return {
        "action": "review",
        "document_id": receipt.document_id,
        "expected_revision": receipt.revision,
        "version_id": receipt.version_id,
        "content_sha256": receipt.content_sha256,
        "snapshot_sha256": receipt.snapshot_sha256,
        "decision": decision,
        "confirm": True,
        "note": "Reviewed this presentation.",
    }


async def test_save_review_edit_and_archive_keep_exact_private_history(
    db, learner, session_factory
):
    spec = await ask_spec(db, learner)
    repo = VisualRepository(session_factory)
    first = await repo.execute(learner.id, "save", raw(save_command(spec)))
    approved = await repo.execute(learner.id, "review", raw(review_command(first)))
    spec["title"] = "Revised presentation"
    second = await repo.execute(learner.id, "edit", raw(save_command(spec, approved)))
    assert second.revision == 3 and second.version_id != first.version_id
    async with session_factory() as check:
        versions = (await check.scalars(select(Version).order_by(Version.version))).all()
        assert [v.version for v in versions] == [1, 2]
        assert versions[0].content_sha256 == first.content_sha256
        assert versions[0].origin_json["grounding_at_save"] == "ungrounded"
        assert versions[1].origin_json["kind"] == "learner"
        assert (await check.scalar(select(Review))).version_id == first.version_id
        assert await check.scalar(select(func.count()).select_from(Snapshot)) == 2
        for table in (LearningEvent, ModelCall):
            assert await check.scalar(select(func.count()).select_from(table)) == 0
    stale = review_command(first)
    stale["expected_revision"] = second.revision
    with pytest.raises(AppError, match="newer version"):
        await repo.execute(learner.id, "old-review", raw(stale))
    archive = {
        "action": "archive",
        "document_id": first.document_id,
        "expected_revision": second.revision,
        "archived": True,
    }
    archived = await repo.execute(learner.id, "archive", raw(archive))
    with pytest.raises(AppError, match="Restore"):
        await repo.execute(learner.id, "archived-save", raw(save_command(spec, archived)))
    restored = await repo.execute(
        learner.id,
        "restore",
        raw({**archive, "expected_revision": archived.revision, "archived": False}),
    )
    assert not restored.archived
    # Retry remains the original receipt, not a new claim that the doc is archived now.
    assert await repo.execute(learner.id, "archive", raw(archive)) == archived
    third = await repo.execute(learner.id, "new-version", raw(save_command(spec, restored)))
    assert third.revision == 6


async def test_concurrent_duplicate_and_conflicting_saves(db, learner, session_factory):
    spec = await ask_spec(db, learner)
    repo = VisualRepository(session_factory)
    body = raw(save_command(spec))
    a, b = await asyncio.gather(
        repo.execute(learner.id, "same", body), repo.execute(learner.id, "same", body)
    )
    assert a == b
    changed = {**spec, "title": "Different"}
    with pytest.raises(AppError, match="different action"):
        await repo.execute(learner.id, "same", raw(save_command(changed)))
    results = await asyncio.gather(
        repo.execute(learner.id, "edit-a", raw(save_command(changed, a))),
        repo.execute(learner.id, "edit-b", raw(save_command(changed, a))),
        return_exceptions=True,
    )
    assert sum(isinstance(r, AppError) for r in results) == 1
    async with session_factory() as check:
        assert await check.scalar(select(func.count()).select_from(Version)) == 2
        assert await check.scalar(select(func.count()).select_from(Operation)) == 2


@pytest.mark.parametrize(
    "change",
    [
        "answer",
        "source",
        "trust",
        "flags",
        "missing_snapshot",
        "missing_source",
        "missing_provenance",
    ],
)
async def test_acceptance_rechecks_live_target_sources_and_grounding(
    db, learner, session_factory, change
):
    spec = await ask_spec(db, learner, sourced=True)
    repo = VisualRepository(session_factory)
    first = await repo.execute(learner.id, "save", raw(save_command(spec)))
    if change == "answer":
        await db.execute(update(TutorAnswer).values(text="Changed answer"))
    elif change == "source":
        await db.execute(update(Chunk).values(text="Changed passage"))
    elif change == "trust":
        await db.execute(update(ChunkProvenance).values(trust_tier=0))
    elif change == "flags":
        await db.execute(
            update(ChunkProvenance).values(trust_tier=1, flags_json=["ignore_previous"])
        )
    elif change == "missing_snapshot":
        await db.execute(delete(Snapshot))  # Simulates learner-scope restoration.
    else:
        await db.execute(delete(ChunkProvenance))
        if change == "missing_source":
            await db.execute(delete(Chunk))
    await db.commit()
    with pytest.raises(AppError) as error:
        await repo.execute(learner.id, "review", raw(review_command(first)))
    assert error.value.http_status == 409
    async with session_factory() as check:
        assert await check.scalar(select(func.count()).select_from(Review)) == 0
        assert await check.scalar(select(Document.revision)) == 1
        assert await check.scalar(select(func.count()).select_from(Operation)) == 1
    # Historical content can still be rejected; no invented reconstruction required.
    rejected = await repo.execute(learner.id, "reject", raw(review_command(first, "reject")))
    assert rejected.review_id


async def test_valid_sourced_review_and_model_identity_are_preserved(db, learner, session_factory):
    spec = await ask_spec(db, learner, sourced=True)
    repo = VisualRepository(session_factory)
    origin = VisualOrigin(kind="model", model="synthetic-local", prompt_version="visual.v1")
    first = await repo.execute(learner.id, "save", raw(save_command(spec)), origin=origin)
    approved = await repo.execute(learner.id, "review", raw(review_command(first)))
    assert approved.review_id
    async with session_factory() as check:
        assert (await check.scalar(select(Version))).origin_json["model"] == "synthetic-local"
    with pytest.raises(AppError, match="different action"):
        await repo.execute(learner.id, "save", raw(save_command(spec)))


async def test_ownership_and_foreign_sources_are_not_accepted(db, learner, session_factory):
    spec = await ask_spec(db, learner)
    other = LearnerProfile(display_name="Other")
    db.add(other)
    await db.commit()
    repo = VisualRepository(session_factory)
    with pytest.raises(AppError):
        await repo.execute(other.id, "foreign-target", raw(save_command(spec)))
    first = await repo.execute(learner.id, "save", raw(save_command(spec)))
    for body in (
        save_command(spec, first),
        review_command(first),
        {
            "action": "archive",
            "document_id": first.document_id,
            "expected_revision": 1,
            "archived": True,
        },
    ):
        with pytest.raises(AppError) as error:
            await repo.execute(other.id, "foreign-document", raw(body))
        assert error.value.http_status == 404
    spec["source_chunk_ids"] = ["unrelated"]
    with pytest.raises(AppError):
        await repo.execute(learner.id, "invented-source", raw(save_command(spec)))


@pytest.mark.parametrize("failure", [RuntimeError, asyncio.CancelledError])
async def test_failed_save_rolls_back_every_write_and_does_not_touch_caller_drafts(
    db, learner, session_factory, monkeypatch, failure
):
    spec = await ask_spec(db, learner)
    repo = VisualRepository(session_factory)
    row = await db.get(TutorAnswer, "root")
    row.text = "Uncommitted learner draft"
    original = repo._save

    async def fail(*args, **kwargs):
        await original(*args, **kwargs)
        raise failure("injected failure")

    monkeypatch.setattr(repo, "_save", fail)
    with pytest.raises(failure, match="injected"):
        await repo.execute(learner.id, "save", raw(save_command(spec)))
    assert row.text == "Uncommitted learner draft" and row in db.dirty
    async with session_factory() as check:
        for table in (Document, Version, Snapshot, Review, Operation):
            assert await check.scalar(select(func.count()).select_from(table)) == 0
    monkeypatch.setattr(repo, "_save", original)
    assert (await repo.execute(learner.id, "save", raw(save_command(spec)))).version_id


async def test_lesson_spec_remains_supported(db, learner, session_factory):
    binding = await lesson_seed(db)
    db.add(
        ChunkProvenance(
            chunk_id="chunk",
            source_id="synthetic",
            path="local",
            source_type="manual",
            trust_tier=2,
        )
    )
    await db.commit()
    spec = {
        "schema_version": "visual.v1",
        "kind": "relationship",
        "binding": binding.model_dump(mode="json"),
        "title": "Leakage",
        "text_equivalent": "Fit training data only.",
        "directed": True,
        "nodes": [
            {
                "id": "fit",
                "label": "Fit",
                "explanation": "Use training data.",
                "source_chunk_ids": ["chunk"],
            }
        ],
        "edges": [],
    }
    repo = VisualRepository(session_factory)
    first = await repo.execute(learner.id, "save", raw(save_command(spec)))
    assert (await repo.execute(learner.id, "review", raw(review_command(first)))).review_id


async def test_strict_schema_and_payload_limits(db, learner):
    spec = await ask_spec(db, learner)
    body = save_command(spec)
    for patch in (
        {"javascript": "alert(1)"},
        {"origin": {"kind": "model"}},
        {"expected_revision": "0"},
    ):
        with pytest.raises(ValidationError):
            parse_command(raw({**body, **patch}))
    with pytest.raises(ValueError, match="byte limit"):
        parse_command(b" " * 131073)
    spec["edges"][0]["target"] = "invented"
    with pytest.raises(ValidationError, match="endpoint"):
        parse_command(raw(save_command(spec)))


async def test_concurrent_reviews_and_displayed_hash_mismatch(db, learner, session_factory):
    spec = await ask_spec(db, learner)
    repo = VisualRepository(session_factory)
    first = await repo.execute(learner.id, "save", raw(save_command(spec)))
    wrong = {**review_command(first), "content_sha256": "0" * 64}
    with pytest.raises(AppError, match="displayed content"):
        await repo.execute(learner.id, "wrong-hash", raw(wrong))
    body = raw(review_command(first))
    a, b = await asyncio.gather(
        repo.execute(learner.id, "review", body), repo.execute(learner.id, "review", body)
    )
    assert a == b
    with pytest.raises(AppError, match="document changed"):
        await repo.execute(learner.id, "another-review", body)
    async with session_factory() as check:
        assert await check.scalar(select(func.count()).select_from(Review)) == 1
        assert await check.scalar(select(func.count()).select_from(Operation)) == 2


async def test_unknown_lineage_can_be_saved_but_not_accepted(db, learner, session_factory):
    spec = await ask_spec(db, learner)
    answer = await db.get(TutorAnswer, "root")
    answer.metadata_json = {"model": "legacy", "prompt_version": "legacy"}
    await db.commit()
    spec["binding"] = (await resolve_answer_binding(db, learner.id, "root")).binding.model_dump(
        mode="json"
    )
    repo = VisualRepository(session_factory)
    first = await repo.execute(learner.id, "save", raw(save_command(spec)))
    with pytest.raises(AppError, match="grounding changed"):
        await repo.execute(learner.id, "review", raw(review_command(first)))
    async with session_factory() as check:
        assert (await check.scalar(select(Version))).origin_json["grounding_at_save"] == "unknown"
