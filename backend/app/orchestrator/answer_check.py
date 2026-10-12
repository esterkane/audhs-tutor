"""Explicit local passage review, independent of answer generation and learning state."""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db import answer_checks, ask_requests
from app.db.models import AnswerCheck, Chunk, ChunkProvenance
from app.db.traces import TutorTraceRecord, write_tutor_trace
from app.models_ai.gateway import ModelGateway
from app.models_ai.provider import Message, TaskClass
from app.orchestrator.answer_check_binding import bind_review, load_bound_review, text_hash
from app.orchestrator.ask import owned_answer
from app.orchestrator.context import QUARANTINE_FLAGS, escape_data
from app.orchestrator.prompts import _read
from app.orchestrator.tools import TUTOR_MIN_TRUST
from app.schemas.answer_checks import AnswerCheckRequest, AnswerReviewProposal

PROMPT_VERSION = "ask.check.v1"
MAX_INPUT_CHARS = 24000


async def read_current(
    db: AsyncSession, learner_id: str, check_id: str
) -> tuple[AnswerCheck, bool]:
    row = await answer_checks.owned(db, learner_id, check_id)
    answer = await owned_answer(db, learner_id, row.answer_id)
    await db.refresh(answer)
    from app.schemas.answer_checks import SavedAnswerReview

    try:
        receipt = SavedAnswerReview.model_validate_json(row.receipt_json)
        sources = await db.scalars(
            select(Chunk)
            .where(Chunk.id.in_(receipt.passage_hashes))
            .execution_options(populate_existing=True)
        )
        passages = {source.id: source.text for source in sources}
        load_bound_review(row.receipt_json, answer.text, passages)
    except ValueError:
        return row, False
    return row, True


async def review(
    db: AsyncSession,
    gateway: ModelGateway,
    learner_id: str,
    body: AnswerCheckRequest,
    key: str,
    *,
    quarantine_below_trust: int = 2,
) -> tuple[AnswerCheck, bool]:
    payload = {"operation": "answer_check.v1", **body.model_dump(mode="json")}
    replay = await ask_requests.replay(db, learner_id, key, payload)
    if replay:
        return await read_current(db, learner_id, str(replay[1]["check_id"]))
    answer = await owned_answer(db, learner_id, body.answer_id)
    rows = await db.scalars(select(Chunk).where(Chunk.id.in_(body.passage_ids)))
    passages = {row.id: row.text for row in rows}
    if len(passages) != len(body.passage_ids):
        raise AppError("source_unavailable", "A selected passage is unavailable.", 404)
    provenance = list(
        await db.scalars(
            select(ChunkProvenance).where(ChunkProvenance.chunk_id.in_(body.passage_ids))
        )
    )
    if len(provenance) != len(passages) or any(
        p.trust_tier < TUTOR_MIN_TRUST
        or (p.trust_tier < quarantine_below_trust and QUARANTINE_FLAGS.intersection(p.flags_json))
        for p in provenance
    ):
        raise AppError(
            "source_excluded",
            "A selected passage is excluded by source trust settings. Search and select again.",
            422,
        )
    if any(text_hash(text) != body.passage_hashes[key] for key, text in passages.items()):
        raise AppError(
            "source_changed",
            "A selected passage changed after selection. Search and select it again.",
            409,
        )
    answer_text = answer.text
    if len(answer_text) + sum(map(len, passages.values())) > MAX_INPUT_CHARS:
        raise AppError("check_too_large", "Choose fewer or shorter source passages.", 422)
    identity, completed = await ask_requests.claim(db, learner_id, key, payload)
    if completed:
        return await read_current(db, learner_id, str(completed["check_id"]))
    # Local gateway policy also applies to structured-output repairs and fallbacks.
    result = await gateway.complete(
        TaskClass.CHAT,
        [
            Message(role="system", content=_read("ask/check.v1.md")),
            Message(
                role="user",
                content="<review_data>\n"
                + escape_data(
                    json.dumps({"answer": answer_text, "passages": passages}, ensure_ascii=False)
                )
                + "\n</review_data>",
            ),
        ],
        response_model=AnswerReviewProposal,
        learner_id=learner_id,
        session_id=None,
        max_tokens=2400,
        metadata={
            "surface": "ask_check",
            "prompt_version": PROMPT_VERSION,
            "answer_id": body.answer_id,
            "answer_hash": text_hash(answer_text),
            "turn_id": identity,
        },
    )
    try:
        proposal = AnswerReviewProposal.model_validate(result.result.parsed)
        bound = bind_review(answer_text, passages, proposal)
    except ValueError as exc:
        raise AppError(
            "check_output_invalid",
            "The review could not be matched to the answer and selected passages. "
            "Your original answer is unchanged; no check was saved. "
            "This request will not run again automatically.",
            422,
        ) from exc
    try:
        row = await answer_checks.save(
            db,
            learner_id=learner_id,
            answer_id=body.answer_id,
            model_call_id=result.model_call_id,
            prompt_version=PROMPT_VERSION,
            receipt_json=bound.receipt_json,
        )
        await write_tutor_trace(
            db,
            TutorTraceRecord(
                learner_id=learner_id,
                session_id=None,
                turn_id=identity,
                action="ask_check",
                prompt_version=PROMPT_VERSION,
                model_call_id=result.model_call_id,
                latency_ms=result.result.latency_ms,
            ),
            commit=False,
        )
        await ask_requests.complete(db, learner_id, identity, {"check_id": row.id})
        await db.commit()
    except BaseException:
        await db.rollback()
        raise
    return await read_current(db, learner_id, row.id)
