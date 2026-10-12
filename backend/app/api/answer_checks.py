"""Local model checks are distinct from answer generation and assessment evidence."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header
from sqlalchemy import select

from app.api.deps import DB, Gateway, Learner, SettingsDep
from app.db.models import AnswerCheck
from app.orchestrator import answer_check, answer_check_read
from app.orchestrator.ask import owned_answer
from app.schemas.answer_checks import AnswerCheckDetail, AnswerCheckPage, AnswerCheckRequest

router = APIRouter(prefix="/answer-checks", tags=["answer-checks"])


@router.post(
    "", response_model=AnswerCheckDetail, summary="Review an answer against selected local passages"
)
async def create_check(
    body: AnswerCheckRequest,
    db: DB,
    gateway: Gateway,
    learner: Learner,
    settings: SettingsDep,
    idempotency_key: Annotated[UUID, Header()],
) -> AnswerCheckDetail:
    row, _ = await answer_check.review(
        db,
        gateway,
        learner.id,
        body,
        str(idempotency_key),
        quarantine_below_trust=settings.quarantine_below_trust,
    )
    return await answer_check_read.detail(db, learner.id, row.id)


@router.get(
    "/answer/{answer_id}",
    response_model=AnswerCheckPage,
    summary="Read saved checks without generating or checking again",
)
async def list_checks(answer_id: str, db: DB, learner: Learner) -> AnswerCheckPage:
    await owned_answer(db, learner.id, answer_id)
    ids = list(
        await db.scalars(
            select(AnswerCheck.id)
            .where(
                AnswerCheck.answer_id == answer_id,
                AnswerCheck.learner_id == learner.id,
            )
            .order_by(AnswerCheck.created_at.desc(), AnswerCheck.id.desc())
            .limit(11)
        )
    )
    return AnswerCheckPage(
        items=[await answer_check_read.detail(db, learner.id, key) for key in ids[:10]],
        has_more=len(ids) > 10,
    )


@router.get("/{check_id}", response_model=AnswerCheckDetail, summary="Read one owned saved check")
async def get_check(check_id: str, db: DB, learner: Learner) -> AnswerCheckDetail:
    return await answer_check_read.detail(db, learner.id, check_id)
