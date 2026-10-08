"""Explicit learner practice eligibility; no assessment or mastery writes."""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import DB, Learner
from app.db.models import Assessment, QuestionState, ReviewItem, SkillNode
from app.kernel import question_corrections, question_state
from app.schemas.question_corrections import CorrectionInbox
from app.schemas.question_state import QuestionStateOut, QuestionTransitionIn

router = APIRouter(prefix="/questions", tags=["questions"])


class QuestionPracticeView(BaseModel):
    status: QuestionStateOut
    skill_title: str
    question: str
    affected_reviews: int


class ExcludedQuestions(BaseModel):
    items: list[QuestionPracticeView]
    total: int
    offset: int
    limit: int


async def preview(db: DB, learner_id: str, assessment_id: str) -> QuestionPracticeView:
    state = await question_state.read(db, learner_id, assessment_id)
    row = (
        await db.execute(
            select(Assessment, SkillNode.title)
            .join(SkillNode, SkillNode.id == Assessment.skill_id)
            .where(Assessment.id == assessment_id)
        )
    ).one()
    a, title = row
    payload = a.item_json
    # Only public question wording; never answer, solution, rubric or hidden key.
    question = str(
        payload.get("question") or payload.get("prompt") or payload.get("text") or "Question"
    )
    count = await db.scalar(
        select(func.count())
        .select_from(ReviewItem)
        .where(
            ReviewItem.learner_id == learner_id,
            ReviewItem.active.is_(True),
            question_state.review_reference() == assessment_id,
            func.coalesce(ReviewItem.prompt_json["type"].as_string(), "") != "vocab",
        )
    )
    return QuestionPracticeView(
        status=state, skill_title=title, question=question[:2000], affected_reviews=int(count or 0)
    )


@router.get("/corrections", response_model=CorrectionInbox, summary="Read your reported questions")
async def corrections(
    db: DB, learner: Learner, offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=50)
) -> CorrectionInbox:
    return await question_corrections.inbox(db, learner.id, offset, limit)


@router.get(
    "/excluded",
    response_model=ExcludedQuestions,
    summary="Your excluded questions and restoration options",
)
async def excluded(
    db: DB, learner: Learner, offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=50)
) -> ExcludedQuestions:
    stmt = select(QuestionState.assessment_id).where(
        QuestionState.learner_id == learner.id, QuestionState.state != "active"
    )
    total = int(await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    ids = list(
        (
            await db.scalars(
                stmt.order_by(QuestionState.updated_at.desc(), QuestionState.assessment_id)
                .offset(offset)
                .limit(limit)
            )
        ).all()
    )
    items = [await preview(db, learner.id, assessment_id) for assessment_id in ids]
    return ExcludedQuestions(items=items, total=total, offset=offset, limit=limit)


@router.get(
    "/{assessment_id}/practice",
    response_model=QuestionPracticeView,
    summary="Preview question eligibility and affected review cards",
)
async def practice(assessment_id: str, db: DB, learner: Learner) -> QuestionPracticeView:
    return await preview(db, learner.id, assessment_id)


@router.post(
    "/{assessment_id}/practice",
    response_model=QuestionStateOut,
    summary="Explicitly suspend or restore one question for yourself",
)
async def change(
    assessment_id: str, body: QuestionTransitionIn, db: DB, learner: Learner
) -> QuestionStateOut:
    learner_id = learner.id
    await db.commit()  # Close only dependency reads before the revision/receipt write lock.
    try:
        result = await question_state.transition(db, learner_id, assessment_id, body)
        await db.commit()
        return result
    except BaseException:
        await db.rollback()
        raise
