"""Opt-in historical reopening, never a factual verification or source-rights grant."""

import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.answer_eligibility import excluded_answer_ids
from app.db.answer_sources import check_many
from app.db.answer_suggestions import context_dependent
from app.db.models import AnswerCheck, Chunk, ModelRegistry, TutorAnswer, TutorAnswerFeedback
from app.models_ai.gateway import ModelGateway
from app.models_ai.provider import Message, TaskClass
from app.orchestrator.answer_check_binding import load_bound_review
from app.schemas.answer_checks import SavedAnswerReview
from app.schemas.ask import AskQuestion


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


async def input_binding(
    db: AsyncSession,
    gateway: ModelGateway,
    learner_id: str,
    packet: list[Message],
    sources: list[dict[str, Any]],
    body: AskQuestion,
) -> tuple[str, str]:
    route = await gateway.router.resolve(db, TaskClass.CHAT, learner_id)
    model = await db.get(ModelRegistry, route.registry_id, populate_existing=True)
    assert model is not None
    return digest(
        {
            "version": 1,
            "request": body.model_dump(exclude={"prefer_saved"}),
            "packet": [message.model_dump() for message in packet],
            "sources": sources,
            "registry": [
                model.id,
                model.updated_at,
                model.runtime,
                model.repo_id,
                model.file_or_tag,
            ],
        }
    ), model.id


async def exact_saved(
    db: AsyncSession, learner_id: str, body: AskQuestion, binding: str
) -> TutorAnswer | None:
    if not body.prefer_saved or body.parent_answer_id:
        return None
    rows = list(
        (
            await db.scalars(
                select(TutorAnswer)
                .join(TutorAnswerFeedback, TutorAnswerFeedback.answer_id == TutorAnswer.id)
                .where(
                    TutorAnswer.learner_id == learner_id,
                    TutorAnswerFeedback.learner_id == learner_id,
                    TutorAnswerFeedback.verdict == "helpful",
                    TutorAnswer.id.not_in(excluded_answer_ids(learner_id)),
                    TutorAnswer.surface == "ask",
                    TutorAnswer.metadata_json["reuse_input_binding"].as_string() == binding,
                )
                .order_by(TutorAnswer.id.desc())
                .limit(20)
                .execution_options(populate_existing=True)
            )
        ).all()
    )
    for row in rows:
        if context_dependent(row) or row.metadata_json.get("reuse_answer_hash") != digest(row.text):
            continue
        check = (await check_many(db, learner_id, [row]))[row.id]
        if check.omitted or any(s.status != "unchanged" or s.newer_version for s in check.sources):
            continue
        receipts = list(
            (
                await db.scalars(
                    select(AnswerCheck)
                    .where(
                        AnswerCheck.learner_id == learner_id,
                        AnswerCheck.answer_id == row.id,
                    )
                    .limit(26)
                )
            ).all()
        )
        if len(receipts) > 25:
            continue
        review_sources = []
        invalid = False
        for receipt in receipts:
            try:
                raw = json.loads(receipt.receipt_json)
                if not isinstance(raw, dict) or not {
                    "version",
                    "method",
                    "coverage",
                    "answer_hash",
                    "passage_hashes",
                    "proposal",
                }.issubset(raw):
                    raise ValueError("Incomplete review receipt")
                review = SavedAnswerReview.model_validate(raw)
            except ValueError:
                invalid = True
                break
            if review.answer_hash != hashlib.sha256(row.text.encode()).hexdigest() or any(
                claim.verdict != "supported" for claim in review.proposal.claims
            ):
                invalid = True
                break
            review_sources.append(
                TutorAnswer(
                    id=receipt.id,
                    learner_id=learner_id,
                    metadata_json={"source_text_hashes": review.passage_hashes},
                )
            )
        if invalid:
            continue
        passage_ids = {
            key for source in review_sources for key in source.metadata_json["source_text_hashes"]
        }
        passages = (
            dict(
                (await db.execute(select(Chunk.id, Chunk.text).where(Chunk.id.in_(passage_ids))))
                .tuples()
                .all()
            )
            if passage_ids
            else {}
        )
        try:
            for receipt in receipts:
                load_bound_review(receipt.receipt_json, row.text, passages)
        except ValueError:
            continue
        reviews = await check_many(db, learner_id, review_sources)
        if any(
            c.omitted or any(s.status != "unchanged" or s.newer_version for s in c.sources)
            for c in reviews.values()
        ):
            continue
        return row
    return None
