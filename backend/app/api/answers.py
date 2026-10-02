"""Local saved history. Reopening never regenerates or awards learning evidence."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DB, Gateway, Learner
from app.core.answer_recovery import MAX_RECEIPT
from app.core.errors import AppError
from app.db import answer_feedback, answer_replacement, answer_sources, workspace_requests
from app.db.answer_eligibility import excluded_answer_ids
from app.db.answer_search import literal_query
from app.db.answers import save_completed
from app.db.models import TutorAnswer
from app.orchestrator import playground
from app.schemas.answers import (
    AnswerDetail,
    AnswerFeedbackState,
    AnswerFollowup,
    AnswerPage,
    AnswerReplacementState,
    AnswerSummary,
    SavedSourceCheck,
)
from app.schemas.playground import PlaygroundContext, PlaygroundReply, PlaygroundRequest

router = APIRouter(prefix="/answers", tags=["answers"])


class AnswerSaveReceipt(BaseModel):
    receipt: str = Field(min_length=1, max_length=MAX_RECEIPT)


class AnswerSaveResult(BaseModel):
    answer_id: str


@router.post(
    "/recover-save",
    response_model=AnswerSaveResult,
    summary="Retry saving a completed answer without regeneration",
)
async def recover_save(
    body: AnswerSaveReceipt,
    db: DB,
    learner: Learner,
    request: Request,
) -> AnswerSaveResult:
    snapshot = request.app.state.answer_recovery.read(body.receipt, learner.id)
    try:
        answer = await save_completed(db, **snapshot)
    except SQLAlchemyError as exc:
        raise AppError(
            "answer_save_failed",
            "The database is still unavailable. Keep the answer and retry saving.",
            http_status=503,
        ) from exc
    return AnswerSaveResult(answer_id=answer.id)


def summary(row: TutorAnswer) -> AnswerSummary:
    # Current request text can be an action instruction. Do not label it a verbatim
    # learner question or synthesize a FAQ title from private code/history.
    request = row.request_json.get("text", row.request_json.get("question", ""))
    question = row.request_json.get("learner_question")
    context = row.metadata_json.get("learning_context")
    label = context.get("target_label") if isinstance(context, dict) else None
    skill = row.metadata_json.get("skill_id")
    area = row.metadata_json.get("area_id")
    return AnswerSummary(
        id=row.id,
        turn_id=row.turn_id,
        session_id=row.session_id,
        surface=row.surface,
        created_at=row.created_at,
        request_text=request if isinstance(request, str) else "",
        learner_question=question if isinstance(question, str) else None,
        target_label=label if isinstance(label, str) else None,
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
    course_id: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    section_id: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    target_id: Annotated[str | None, Query(min_length=1, max_length=1000)] = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    parent_answer_id: Annotated[str | None, Query(min_length=1, max_length=128)] = None,
    suggestions: bool = False,
    surface: Literal["tutor", "playground", "representation"] | None = None,
) -> AnswerPage:
    stmt = select(TutorAnswer).where(TutorAnswer.learner_id == learner.id)
    if parent_answer_id is not None:
        await answer_feedback.owned(db, learner.id, parent_answer_id)
        stmt = stmt.where(
            TutorAnswer.metadata_json["parent_answer_id"].as_string() == parent_answer_id
        )
    if suggestions:
        excluded = excluded_answer_ids(learner.id)
        stmt = stmt.where(TutorAnswer.id.not_in(excluded))
    if q is not None and q.strip():
        expression = literal_query(q)
        if expression is None:
            return AnswerPage(items=[], next_cursor=None)
        stmt = stmt.where(
            TutorAnswer.id.in_(
                select(text("id"))
                .select_from(text("tutor_answer_fts"))
                .where(text("tutor_answer_fts MATCH :search_expression"))
            )
        ).params(search_expression=expression)
    for key, value in (
        ("course_id", course_id),
        ("section_id", section_id),
        ("target_id", target_id),
    ):
        if value is not None:
            stmt = stmt.where(
                TutorAnswer.metadata_json["learning_context"][key].as_string() == value
            )
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


@router.post(
    "/{answer_id}/followup",
    response_model=PlaygroundReply,
    summary="Ask about an owned saved answer",
)
async def followup(
    answer_id: str,
    body: AnswerFollowup,
    db: DB,
    learner: Learner,
    gateway: Gateway,
    request: Request,
    idempotency_key: Annotated[UUID | None, Header()] = None,
) -> PlaygroundReply:
    row = await db.scalar(
        select(TutorAnswer).where(TutorAnswer.id == answer_id, TutorAnswer.learner_id == learner.id)
    )
    if row is None:
        raise KeyError("saved answer not found")
    learner_id = learner.id
    identity = None
    if idempotency_key is not None:
        identity, saved = await workspace_requests.claim(
            db,
            learner_id,
            body.session_id,
            str(idempotency_key),
            {
                "surface": "answer_followup",
                "parent_answer_id": answer_id,
                **body.model_dump(mode="json", exclude={"purpose"}),
                **({"purpose": "correction"} if body.purpose == "correction" else {}),
            },
        )
        if saved is not None:
            return PlaygroundReply.model_validate(saved)
    clipped: list[str] = []

    def excerpt(value: object, maximum: int, label: str) -> str:
        text_value = value if isinstance(value, str) else ""
        if len(text_value) > maximum:
            clipped.append(label)
        return text_value[:maximum]

    old = row.request_json
    historical = {
        "parent_answer_id": row.id,
        "purpose": body.purpose,
        "learner_report": (await answer_feedback.read(db, learner.id, row.id)).model_dump(),
        "saved_at": row.created_at,
        "request": excerpt(old.get("question", old.get("text")), 2000, "earlier request"),
        "answer": excerpt(row.text, 8000, "earlier answer"),
        "learner_answer": excerpt(old.get("learner_answer"), 8000, "earlier learner answer"),
        "limitations": (
            "Historical context only. Original retrieved passages and earlier chat are not supplied. "
            "No current source verification or execution."
        ),
        "truncated_fields": clipped,
    }
    context = row.metadata_json.get("learning_context")
    workspace_request = PlaygroundRequest(
        session_id=body.session_id,
        question=body.question,
        learner_question=body.question,
        exercise=excerpt(old.get("exercise"), 1000, "material"),
        code=excerpt(old.get("code"), 16000, "code"),
        output=excerpt(old.get("output"), 4000, "output"),
        output_stale=True,
        learning_context=PlaygroundContext.model_validate(context)
        if isinstance(context, dict)
        else None,
    )
    reply = await playground.respond(
        db,
        gateway,
        learner_id,
        workspace_request,
        historical=historical,
        recovery=request.app.state.answer_recovery,
        parent_metadata={
            "parent_answer_id": row.id,
            "followup_purpose": body.purpose,
            "skill_id": row.metadata_json.get("skill_id"),
            "area_id": row.metadata_json.get("area_id"),
        },
    )

    if identity is not None:
        await workspace_requests.complete(db, learner_id, identity, reply.model_dump(mode="json"))
    return reply


@router.get(
    "/{answer_id}/feedback",
    response_model=AnswerFeedbackState,
    summary="Read your saved-answer feedback",
)
async def get_feedback(answer_id: str, db: DB, learner: Learner) -> AnswerFeedbackState:
    return await answer_feedback.read(db, learner.id, answer_id)


@router.put(
    "/{answer_id}/feedback",
    response_model=AnswerFeedbackState,
    summary="Save reversible feedback without changing learning evidence",
)
async def put_feedback(
    answer_id: str, body: AnswerFeedbackState, db: DB, learner: Learner
) -> AnswerFeedbackState:
    return await answer_feedback.save(db, learner.id, answer_id, body)


@router.get(
    "/{answer_id}/source-status",
    response_model=SavedSourceCheck,
    summary="Compare saved source text with the current local corpus",
)
async def source_status(answer_id: str, db: DB, learner: Learner) -> SavedSourceCheck:
    return await answer_sources.check(db, learner.id, answer_id)


@router.get(
    "/{answer_id}/replacement",
    response_model=AnswerReplacementState,
    summary="Read your preferred correction without changing history",
)
async def get_replacement(answer_id: str, db: DB, learner: Learner) -> AnswerReplacementState:
    return await answer_replacement.read(db, learner.id, answer_id)


@router.put(
    "/{answer_id}/replacement",
    response_model=AnswerReplacementState,
    summary="Choose or undo a preferred correction while retaining both answers",
)
async def put_replacement(
    answer_id: str, body: AnswerReplacementState, db: DB, learner: Learner
) -> AnswerReplacementState:
    return await answer_replacement.save(db, learner.id, answer_id, body)
