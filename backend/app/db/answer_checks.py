"""Owned, append-only local-review receipts. Does not certify model verdicts."""

import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models import AnswerCheck, ModelCall, TutorAnswer
from app.schemas.answer_checks import SavedAnswerReview


async def save(
    db: AsyncSession,
    *,
    learner_id: str,
    answer_id: str,
    model_call_id: str,
    prompt_version: str,
    receipt_json: str,
) -> AnswerCheck:
    answer = await db.scalar(
        select(TutorAnswer)
        .where(TutorAnswer.id == answer_id, TutorAnswer.learner_id == learner_id)
        .execution_options(populate_existing=True)
    )
    call = await db.scalar(
        select(ModelCall).where(ModelCall.id == model_call_id, ModelCall.learner_id == learner_id)
    )
    if answer is None or call is None:
        raise AppError("not_found", "Answer or review call is unavailable.", 404)
    if call.provider != "ollama" or not call.ok:
        raise AppError("invalid_review", "Only a completed local model review can be saved.", 422)
    receipt = SavedAnswerReview.model_validate_json(receipt_json)
    if receipt.answer_hash != hashlib.sha256(answer.text.encode("utf-8")).hexdigest():
        raise AppError("answer_changed", "The answer changed while its check was running.", 409)
    if call.outcome != "ok" or any(
        call.metadata_json.get(key) != value
        for key, value in {
            "surface": "ask_check",
            "answer_id": answer_id,
            "answer_hash": receipt.answer_hash,
            "prompt_version": prompt_version,
        }.items()
    ):
        raise AppError("invalid_review", "The model call does not match this answer check.", 422)
    existing = await db.scalar(
        select(AnswerCheck).where(
            AnswerCheck.learner_id == learner_id, AnswerCheck.model_call_id == model_call_id
        )
    )
    if existing:
        if (existing.answer_id, existing.prompt_version, existing.receipt_json) != (
            answer_id,
            prompt_version,
            receipt_json,
        ):
            raise AppError("review_conflict", "This model call already has another review.", 409)
        return existing
    row = AnswerCheck(
        learner_id=learner_id,
        answer_id=answer_id,
        model_call_id=model_call_id,
        prompt_version=prompt_version,
        receipt_json=receipt_json,
    )
    db.add(row)
    await db.flush()
    return row


async def owned(db: AsyncSession, learner_id: str, check_id: str) -> AnswerCheck:
    row = await db.scalar(
        select(AnswerCheck).where(AnswerCheck.id == check_id, AnswerCheck.learner_id == learner_id)
    )
    if row is None:
        raise AppError("not_found", "This answer check is unavailable.", 404)
    return row
