import copy
from uuid import uuid4

import pytest

from app.db import models
from app.kernel import correction_drafts as drafts
from app.kernel import correction_sources, correction_validation
from app.schemas.correction_drafts import CreateCorrectionDraft
from tests.test_question_state import item

MCQ = {
    "question": "Which option?",
    "options": ["First", "Second"],
    "answer": 0,
    "explanation": "Reason.",
}


def validate(kind, payload, rubric=None, candidate=None):
    original = {"kind": kind, "item": payload, "rubric": rubric}
    return correction_validation.review(original, candidate or {"item": payload, "rubric": rubric})


@pytest.mark.parametrize(
    "payload",
    [
        {**MCQ, "answer": True},
        {**MCQ, "answer": 2},
        {**MCQ, "answer": "0"},
        {**MCQ, "options": ["Same", " same "]},
        {**MCQ, "explanation": ""},
    ],
)
def test_rejects_invalid_mcq(payload):
    assert validate("mcq", payload)


def test_shapes_and_metadata_preservation():
    original = {
        **MCQ,
        "listening": {"chunk_id": "c", "t_start": 1, "validated": False},
        "source_chunk_id": "c",
    }
    candidate = {"item": {**original, "question": "A corrected question?"}, "rubric": None}
    before = copy.deepcopy(candidate)
    assert not validate("mcq", original, candidate=candidate)
    assert candidate == before
    candidate["item"]["listening"] = {"chunk_id": "another"}
    assert "metadata" in validate("mcq", original, candidate=candidate)[0]["message"]
    assert not validate("cloze", {"text": "Fill ___", "answers": ["Python"]})
    assert validate("cloze", {"text": "Fill ___", "answers": ["!!!"]})
    rubric = [{"criterion": "Explains the cause", "keywords": ["cause"]}]
    assert not validate("explain_back", {"prompt": "Explain why."}, rubric)
    assert validate("explain_back", {"prompt": "Explain why."}, [])
    assert validate("transfer", {"prompt": "Apply it."}, rubric * 2)
    assert validate("code", {"prompt": "Implement this."})
    assert validate("unknown", {})


def test_challenge_criteria_and_rubric_agree():
    payload = {
        "prompt": "Find the incorrect step.",
        "hidden_key": "The second step is wrong.",
        "criteria": ["Find the error", "Explain the correction"],
        "mode": "planted_error",
    }
    rubric = [{"criterion": text, "keywords": []} for text in payload["criteria"]]
    assert not validate("challenge_planted_error", payload, rubric)
    assert validate("challenge_planted_error", payload, list(reversed(rubric)))


async def sourced_question(db):
    q = await item(db)
    document = models.Document(title="Synthetic source", source_type="manual")
    db.add(document)
    await db.flush()
    version = models.DocumentVersion(document_id=document.id, content_hash="v1")
    db.add(version)
    await db.flush()
    chunk = models.Chunk(document_version_id=version.id, ordinal=0, text="Original passage.")
    db.add(chunk)
    await db.flush()
    provenance = models.ChunkProvenance(
        chunk_id=chunk.id, source_id=document.id, path="synthetic.txt", source_type="manual"
    )
    db.add(provenance)
    q.item_json = {**MCQ, "source_chunk_id": chunk.id}
    await db.commit()
    return q, chunk, provenance


async def test_source_identity_changes_and_legacy_are_honest(db, learner):
    q, chunk, provenance = await sourced_question(db)
    first = await drafts.create(
        db,
        learner.id,
        CreateCorrectionDraft(request_id=uuid4(), assessment_id=q.id, expected_question_revision=0),
    )
    await db.commit()
    initial = await drafts.inspect(db, learner.id, first.draft_id)
    assert initial["source_status"] == "unchanged" and not initial["problems"]
    assert not initial["content_changed"] and not initial["publication_available"]
    chunk.text = "Changed text under the same ID and version."
    await db.commit()
    changed = await drafts.inspect(db, learner.id, first.draft_id)
    assert changed["source_status"] == "changed" and not changed["content_changed"]
    chunk.text = "Original passage."
    provenance.trust_tier = 0
    await db.commit()
    assert (await drafts.inspect(db, learner.id, first.draft_id))["source_status"] == "changed"
    row = await drafts.get(db, learner.id, first.draft_id)
    row.original_json = {
        key: value for key, value in row.original_json.items() if key != "source_evidence"
    }
    await db.commit()
    assert (await drafts.inspect(db, learner.id, first.draft_id))["source_status"] == "not_captured"


async def test_incomplete_sources_are_not_verified(db):
    q, chunk, _ = await sourced_question(db)
    assert (await correction_sources.capture(db, {}))["complete"] is False
    assert (await correction_sources.capture(db, {"sources": ["[Label only]"]}))[
        "complete"
    ] is False
    assert (
        await correction_sources.capture(db, {"sources": [chunk.id, {"citation": "Missing ID"}]})
    )["complete"] is False
    assert (await correction_sources.capture(db, {"sources": [str(i) for i in range(65)]}))[
        "reason"
    ] == "too_many_references"
    good = await correction_sources.capture(
        db, {"sources": [{"chunk_id": chunk.id}], "listening": {"chunk_id": chunk.id}}
    )
    assert good["complete"] and len(good["items"]) == 1


@pytest.mark.parametrize("options", [["A!", "A?"], ["a b", "a   b"], ["!!!", "Valid"]])
def test_mcq_options_cannot_alias_under_actual_grader(options):
    assert validate("mcq", {**MCQ, "options": options})


def test_normalization_matches_existing_grader():
    from app.orchestrator.grader import _norm

    for value in ["A!", "A?", "a   b", "√(x)", "CAFÉ", "!!!", "0.5", "x_y"]:
        assert correction_validation.answer_text(value) == _norm(value)
