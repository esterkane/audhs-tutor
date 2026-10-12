from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.errors import AppError
from app.db.models import (
    AnswerCheck,
    Chunk,
    ChunkProvenance,
    Document,
    DocumentVersion,
    Session,
    TutorAnswer,
)
from app.models_ai import registry
from app.models_ai.budget import Budget
from app.models_ai.gateway import ModelGateway
from app.models_ai.routing import Router
from app.orchestrator.answer_check import review
from app.schemas.answer_checks import AnswerCheckRequest


async def setup(db, learner, fake_local):
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    source = Document(title="Synthetic", source_type="manual")
    db.add(source)
    await db.flush()
    version = DocumentVersion(document_id=source.id, content_hash="v1", version=1)
    db.add(version)
    await db.flush()
    passage = Chunk(document_version_id=version.id, ordinal=0, text="A byte has eight bits.")
    answer = TutorAnswer(
        learner_id=learner.id,
        turn_id="a",
        surface="ask",
        request_json={"question": "Explain bytes"},
        text=passage.text,
        metadata_json={},
        fingerprint="test",
    )
    db.add_all([passage, answer])
    await db.flush()
    db.add(
        ChunkProvenance(
            chunk_id=passage.id,
            source_id=source.id,
            path="synthetic",
            source_type="manual",
            trust_tier=2,
        )
    )
    await db.commit()
    fake_local.structured = {
        "claims": [
            {
                "claim_quote": answer.text,
                "verdict": "supported",
                "explanation": "Direct definition.",
                "evidence": [{"passage_id": passage.id, "quote": passage.text}],
            }
        ],
        "limitations": ["Only this claim reviewed."],
    }
    gateway = ModelGateway(db, Router("default"), {"ollama": fake_local}, Budget(0))
    return (
        gateway,
        AnswerCheckRequest(
            answer_id=answer.id,
            passage_ids=[passage.id],
            passage_hashes={
                passage.id: __import__("hashlib").sha256(passage.text.encode()).hexdigest()
            },
        ),
        passage,
    )


async def test_review_replays_without_model_and_detects_changed_source(db, learner, fake_local):
    gateway, body, passage = await setup(db, learner, fake_local)
    key = str(uuid4())
    row, valid = await review(db, gateway, learner.id, body, key)
    assert valid
    assert (await review(db, gateway, learner.id, body, key))[0].id == row.id
    assert len(fake_local.calls) == 1
    passage.text = "Changed definition."
    await db.commit()
    assert not (await review(db, gateway, learner.id, body, key))[1]
    assert len(fake_local.calls) == 1
    assert await db.scalar(select(func.count()).select_from(Session)) == 0


async def test_invented_citation_does_not_save_check_or_regenerate(db, learner, fake_local):
    gateway, body, passage = await setup(db, learner, fake_local)
    fake_local.structured["claims"][0]["evidence"][0]["passage_id"] = "invented"
    key = str(uuid4())
    with pytest.raises(AppError, match="could not be matched"):
        await review(db, gateway, learner.id, body, key)
    with pytest.raises(AppError, match="still running"):
        await review(db, gateway, learner.id, body, key)
    assert len(fake_local.calls) == 1
    assert await db.scalar(select(func.count()).select_from(AnswerCheck)) == 0
    assert await db.get(TutorAnswer, body.answer_id) is not None


async def test_http_check_labels_partial_model_review_and_source_currency(
    client,
    db,
    learner,
    fake_local,
):
    gateway, body, passage = await setup(db, learner, fake_local)
    response = await client.post(
        "/api/answer-checks", json=body.model_dump(), headers={"Idempotency-Key": str(uuid4())}
    )
    assert response.status_code == 200, response.text
    saved = response.json()
    assert saved["method"] == "local_model_review"
    assert saved["coverage"] == "listed_claims_only"
    assert saved["binding_status"] == "unchanged"
    assert "not independent factual verification" in saved["note"]
    version = await db.get(DocumentVersion, passage.document_version_id)
    db.add(DocumentVersion(document_id=version.document_id, version=2, content_hash="v2"))
    await db.commit()
    current = (await client.get(f"/api/answer-checks/{saved['id']}")).json()
    assert current["binding_status"] == "unchanged"
    assert current["passages"][0]["newer_version_available"]
    assert len(fake_local.calls) == 1
    history = (await client.get(f"/api/answer-checks/answer/{body.answer_id}")).json()
    assert history["items"][0]["id"] == saved["id"]
    passage.text = "Edited after review"
    await db.commit()
    stale = (await client.get(f"/api/answer-checks/{saved['id']}")).json()
    assert stale["binding_status"] == "changed_or_missing"
    assert stale["passages"][0]["binding_status"] == "changed"
    assert "historical" in stale["note"]
    assert len(fake_local.calls) == 1


@pytest.mark.parametrize("change", ["untrusted", "flagged", "edited"])
async def test_selection_changes_are_rejected_before_inference(db, learner, fake_local, change):
    from app.orchestrator.context import QUARANTINE_FLAGS

    gateway, body, passage = await setup(db, learner, fake_local)
    provenance = await db.scalar(
        select(ChunkProvenance).where(ChunkProvenance.chunk_id == passage.id)
    )
    if change == "edited":
        passage.text = "Unseen replacement"
    elif change == "untrusted":
        provenance.trust_tier = 0
    else:
        provenance.trust_tier = 1
        provenance.flags_json = [next(iter(QUARANTINE_FLAGS))]
    await db.commit()
    with pytest.raises(AppError) as error:
        await review(db, gateway, learner.id, body, str(uuid4()))
    assert error.value.code == ("source_changed" if change == "edited" else "source_excluded")
    assert not fake_local.calls
