"""Local saved history. Reopening never regenerates or awards learning evidence."""

from typing import Annotated, Literal

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import DB, Learner
from app.db.models import TutorAnswer
from app.schemas.answers import AnswerDetail, AnswerPage, AnswerSummary

router = APIRouter(prefix="/answers", tags=["answers"])


def summary(row: TutorAnswer) -> AnswerSummary:
    # Current request text can be an action instruction. Do not label it a verbatim
    # learner question or synthesize a FAQ title from private code/history.
    request = row.request_json.get("text", row.request_json.get("question", ""))
    skill = row.metadata_json.get("skill_id")
    area = row.metadata_json.get("area_id")
    return AnswerSummary(
        id=row.id,
        turn_id=row.turn_id,
        session_id=row.session_id,
        surface=row.surface,
        created_at=row.created_at,
        request_text=request if isinstance(request, str) else "",
        preview=row.text[:300],
        skill_id=skill if isinstance(skill, str) else None,
        area_id=area if isinstance(area, str) else None,
    )


@router.get(
    "", response_model=AnswerPage, summary="List the current learner's completed saved answers"
)
async def list_answers(
    db: DB,
    learner: Learner,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(min_length=1, max_length=128)] = None,
    skill_id: Annotated[str | None, Query(min_length=1, max_length=128)] = None,
    area_id: Annotated[str | None, Query(min_length=1, max_length=128)] = None,
    surface: Literal["tutor", "playground"] | None = None,
) -> AnswerPage:
    stmt = select(TutorAnswer).where(TutorAnswer.learner_id == learner.id)
    if skill_id is not None:
        stmt = stmt.where(TutorAnswer.metadata_json["skill_id"].as_string() == skill_id)
    if area_id is not None:
        stmt = stmt.where(TutorAnswer.metadata_json["area_id"].as_string() == area_id)
    if surface is not None:
        stmt = stmt.where(TutorAnswer.surface == surface)
    if cursor is not None:
        # Cursors refer to visible rows only; another learner's ID never confirms existence.
        anchor = await db.scalar(
            select(TutorAnswer.id).where(
                TutorAnswer.id == cursor,
                TutorAnswer.learner_id == learner.id,
            )
        )
        if anchor is None:
            raise KeyError("saved answer not found")
        stmt = stmt.where(TutorAnswer.id < cursor)
    rows = list((await db.scalars(stmt.order_by(TutorAnswer.id.desc()).limit(limit + 1))).all())
    return AnswerPage(
        items=[summary(row) for row in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


@router.get(
    "/{answer_id}",
    response_model=AnswerDetail,
    summary="Open one saved answer without regenerating",
)
async def get_answer(answer_id: str, db: DB, learner: Learner) -> AnswerDetail:
    row = await db.scalar(
        select(TutorAnswer).where(
            TutorAnswer.id == answer_id,
            TutorAnswer.learner_id == learner.id,
        )
    )
    if row is None:
        raise KeyError("saved answer not found")
    return AnswerDetail(
        **summary(row).model_dump(),
        text=row.text,
        request=row.request_json,
        metadata=row.metadata_json,
    )
