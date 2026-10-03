from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request
from pydantic import BaseModel

from app.api.deps import DB, Gateway, Learner
from app.core.errors import AppError
from app.db.models import Assessment
from app.kernel import session as ksession
from app.orchestrator import assessment_requests
from app.orchestrator.grader import Grader, versioned_view
from app.schemas.grading import AssessmentView, AttemptRequest, AttemptResult

router = APIRouter(prefix="/assess", tags=["assess"])


class NextItem(BaseModel):
    item: AssessmentView | None
    skill_id: str


@router.get(
    "/next",
    summary="Next assessment item for a skill (mcq → cloze → explain-back rotation)",
    response_model=NextItem,
)
async def next_item(
    db: DB,
    gateway: Gateway,
    learner: Learner,
    session_id: str = Query(...),
    skill_id: str | None = None,
) -> NextItem:
    s = await ksession.get_owned(db, session_id, learner.id)
    if skill_id is None:
        cp = await ksession.load_checkpoint(db, s.id) or {}
        skill_id = cp.get("skill_id")
    if skill_id is None:
        from app.kernel import skill_graph

        nxt = await skill_graph.next_skill(db, learner.id)
        if nxt is None:
            raise KeyError("no skills")
        skill_id = nxt.id
    a = await Grader(db, gateway).next_item(learner.id, skill_id)
    return NextItem(item=await versioned_view(db, a) if a else None, skill_id=skill_id)


@router.post(
    "/attempt",
    summary="Submit an answer with an optional prior confidence rating; graded hierarchically",
    response_model=AttemptResult,
)
async def attempt(
    body: AttemptRequest,
    db: DB,
    gateway: Gateway,
    learner: Learner,
    request: Request,
    idempotency_key: Annotated[UUID | None, Header()] = None,
) -> AttemptResult:
    return await assessment_requests.submit(
        db,
        gateway,
        learner.id,
        body,
        request.app.state.answer_recovery,
        str(idempotency_key) if idempotency_key is not None else None,
    )


@router.get(
    "/requests/{request_id}",
    summary="Read a grading request result without grading or changing progress",
    response_model=assessment_requests.AssessmentRequestState,
)
async def request_result(
    request_id: UUID, session_id: str, db: DB, learner: Learner, request: Request
) -> assessment_requests.AssessmentRequestState:
    return await assessment_requests.lookup(
        db, learner.id, session_id, str(request_id), request.app.state.answer_recovery
    )


@router.get("/items/{assessment_id}", response_model=AssessmentView)
async def refresh_item(
    assessment_id: str, session_id: str, db: DB, learner: Learner
) -> AssessmentView:
    await ksession.get_owned(db, session_id, learner.id)
    item = await db.get(Assessment, assessment_id)
    if item is None:
        raise AppError("not_found", "This assessment is unavailable.", 404)
    return await versioned_view(db, item)
