import json
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.errors import AppError
from app.db import ask_requests
from app.db.models import (
    AnswerCheck,
    AskRequest,
    DocumentVersion,
    LearningEvent,
    ModelCall,
    ModelRegistry,
    Session,
    TutorAnswer,
    TutorAnswerFeedback,
    TutorTrace,
)
from app.orchestrator import ask
from app.schemas.ask import AskQuestion
from tests.test_ask_sources import setup


async def marked(db, learner, fake_local):
    gateway, body, chunk, provenance = await setup(db, learner, fake_local)
    first = await ask.respond(db, gateway, learner.id, body, str(uuid4()))
    db.add(TutorAnswerFeedback(learner_id=learner.id, answer_id=first.answer_id, verdict="helpful"))
    await db.commit()
    return gateway, body, chunk, provenance, first


async def test_opt_in_reuses_original_with_atomic_receipt_and_no_new_model_or_learning(
    db, learner, fake_local
):
    gateway, body, _, _, first = await marked(db, learner, fake_local)
    body = body.model_copy(update={"prefer_saved": True})
    key = str(uuid4())
    result = await ask.respond(db, gateway, learner.id, body, key)
    assert (
        result.reused and result.answer_id == first.answer_id and result.saved_at == first.saved_at
    )
    assert result.text == first.text and result.route == "saved"
    assert len(fake_local.calls) == 1
    assert await ask.respond(db, gateway, learner.id, body, key) == result
    assert len(fake_local.calls) == 1
    assert await db.scalar(select(func.count()).select_from(TutorAnswer)) == 1
    assert await db.scalar(select(func.count()).select_from(AskRequest)) == 2
    trace = await db.scalar(select(TutorTrace).where(TutorTrace.action == "ask_reuse"))
    assert trace.model_call_id is None and trace.retrieval_trace_id
    for model in (Session, LearningEvent):
        assert await db.scalar(select(func.count()).select_from(model)) == 0
    assert await db.scalar(select(func.count()).select_from(ModelCall)) == 1


@pytest.mark.parametrize(
    "change",
    [
        "fresh",
        "question",
        "followup",
        "hidden",
        "confusing",
        "edited",
        "legacy",
        "model",
        "new_version",
        "negative_review",
        "bad_review",
    ],
)
async def test_changed_or_unqualified_answers_generate_instead(db, learner, fake_local, change):
    gateway, body, chunk, _, first = await marked(db, learner, fake_local)
    row = await db.get(TutorAnswer, first.answer_id)
    body = body.model_copy(update={"prefer_saved": True})
    if change == "fresh":
        body = body.model_copy(update={"prefer_saved": False})
    elif change == "question":
        body = body.model_copy(update={"question": body.question + " in detail"})
    elif change == "followup":
        body = body.model_copy(update={"parent_answer_id": first.answer_id})
    elif change in {"hidden", "confusing"}:
        feedback = await db.scalar(select(TutorAnswerFeedback))
        feedback.hidden = change == "hidden"
        feedback.verdict = "confusing" if change == "confusing" else "helpful"
    elif change == "edited":
        row.text = "Changed after saving"
    elif change == "legacy":
        row.metadata_json = {
            k: v for k, v in row.metadata_json.items() if k != "reuse_input_binding"
        }
    elif change == "model":
        model = await db.get(ModelRegistry, first.model)
        model.updated_at = "new revision"
    elif change == "new_version":
        old = await db.get(DocumentVersion, chunk.document_version_id)
        db.add(
            DocumentVersion(
                document_id=old.document_id, version=old.version + 1, content_hash="new"
            )
        )
    else:
        import hashlib

        receipt = (
            "invalid"
            if change == "bad_review"
            else json.dumps(
                {
                    "version": 1,
                    "method": "local_model_review",
                    "coverage": "listed_claims_only",
                    "answer_hash": hashlib.sha256(row.text.encode()).hexdigest(),
                    "passage_hashes": {},
                    "proposal": {
                        "claims": [
                            {
                                "claim_quote": row.text,
                                "verdict": "insufficient",
                                "explanation": "Not supported",
                                "evidence": [],
                            }
                        ]
                    },
                }
            )
        )
        call = await db.scalar(select(ModelCall))
        db.add(
            AnswerCheck(
                learner_id=learner.id,
                answer_id=row.id,
                model_call_id=call.id,
                prompt_version="test",
                receipt_json=receipt,
            )
        )
    await db.commit()
    result = await ask.respond(db, gateway, learner.id, body, str(uuid4()))
    assert not result.reused and result.answer_id != first.answer_id
    assert len(fake_local.calls) == 2


async def test_reuse_receipt_failure_rolls_back_and_never_regenerates(
    db, learner, fake_local, monkeypatch
):
    owner = learner.id
    gateway, body, _, _, _ = await marked(db, learner, fake_local)
    body = body.model_copy(update={"prefer_saved": True})

    async def fail(*args, **kwargs):
        raise RuntimeError("receipt failed")

    monkeypatch.setattr(ask_requests, "complete", fail)
    key = str(uuid4())
    with pytest.raises(RuntimeError, match="receipt failed"):
        await ask.respond(db, gateway, owner, body, key)
    assert await db.scalar(select(func.count()).select_from(TutorTrace)) == 1
    with pytest.raises(AppError, match="still running"):
        await ask.respond(db, gateway, owner, body, key)
    assert len(fake_local.calls) == 1


def test_default_preserves_old_request_fingerprint():
    assert AskQuestion(question="Example").model_dump() == {
        "question": "Example",
        "area_id": None,
        "parent_answer_id": None,
    }


@pytest.mark.parametrize("invented_quote", [False, True])
async def test_review_receipts_require_actual_bound_quotations(
    db, learner, fake_local, invented_quote
):
    import hashlib

    gateway, body, chunk, _, first = await marked(db, learner, fake_local)
    call = await db.scalar(select(ModelCall))
    receipt = {
        "version": 1,
        "method": "local_model_review",
        "coverage": "listed_claims_only",
        "answer_hash": hashlib.sha256(first.text.encode()).hexdigest(),
        "passage_hashes": {chunk.id: hashlib.sha256(chunk.text.encode()).hexdigest()},
        "proposal": {
            "claims": [
                {
                    "claim_quote": first.text,
                    "verdict": "supported",
                    "explanation": "Listed claim only",
                    "evidence": [
                        {
                            "passage_id": chunk.id,
                            "quote": "invented quotation"
                            if invented_quote
                            else "A byte has eight bits.",
                        }
                    ],
                }
            ]
        },
    }
    db.add(
        AnswerCheck(
            learner_id=learner.id,
            answer_id=first.answer_id,
            model_call_id=call.id,
            prompt_version="test",
            receipt_json=json.dumps(receipt),
        )
    )
    await db.commit()
    result = await ask.respond(
        db, gateway, learner.id, body.model_copy(update={"prefer_saved": True}), str(uuid4())
    )
    assert result.reused is not invented_quote
    assert len(fake_local.calls) == (2 if invented_quote else 1)


async def test_eligibility_and_receipt_serialize_with_concurrent_negative_feedback(
    db, learner, fake_local, session_factory, monkeypatch
):
    import asyncio

    from sqlalchemy import update

    from app.orchestrator import ask_reuse

    gateway, body, _, _, first = await marked(db, learner, fake_local)
    owner = learner.id
    original = ask_reuse.exact_saved
    writer = None

    async def change_feedback():
        async with session_factory() as other:
            await other.execute(
                update(TutorAnswerFeedback)
                .where(
                    TutorAnswerFeedback.learner_id == owner,
                    TutorAnswerFeedback.answer_id == first.answer_id,
                )
                .values(verdict="incorrect")
            )
            await other.commit()

    async def inspect(*args):
        nonlocal writer
        candidate = await original(*args)
        writer = asyncio.create_task(change_feedback())
        # The other writer must wait until this reuse's check+receipt transaction ends.
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(asyncio.shield(writer), timeout=0.05)
        return candidate

    monkeypatch.setattr(ask_reuse, "exact_saved", inspect)
    result = await ask.respond(
        db, gateway, owner, body.model_copy(update={"prefer_saved": True}), str(uuid4())
    )
    assert result.reused
    await writer
    monkeypatch.setattr(ask_reuse, "exact_saved", original)
    fresh = await ask.respond(
        db, gateway, owner, body.model_copy(update={"prefer_saved": True}), str(uuid4())
    )
    assert not fresh.reused
