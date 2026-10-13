from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request
from pydantic import BaseModel

from app.api.deps import DB, Gateway, Learner
from app.core.errors import AppError
from app.db.models import Assessment, AssessmentAttempt
from app.kernel import session as ksession
from app.orchestrator import assessment_content, assessment_requests, assessment_revisions
from app.orchestrator.grader import Grader, versioned_view, view
from app.schemas.grading import AssessmentOutcome, AssessmentView, AttemptRequest

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
    return NextItem(item=await versioned_view(db, a, learner.id) if a else None, skill_id=skill_id)


@router.post(
    "/attempt",
    summary="Submit an answer with an optional prior confidence rating; graded hierarchically",
    response_model=AssessmentOutcome,
)
async def attempt(
    body: AttemptRequest,
    db: DB,
    gateway: Gateway,
    learner: Learner,
    request: Request,
    idempotency_key: Annotated[UUID | None, Header()] = None,
) -> AssessmentOutcome:
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
    return await versioned_view(db, item, learner.id)


@router.post("/requests/{request_id}/finish", response_model=AssessmentOutcome)
async def finish_request(
    request_id: UUID,
    session_id: str,
    db: DB,
    gateway: Gateway,
    learner: Learner,
    request: Request,
) -> AssessmentOutcome:
    return await assessment_requests.finish(
        db,
        gateway,
        learner.id,
        session_id,
        str(request_id),
        request.app.state.answer_recovery,
    )


@router.post("/requests/{request_id}/continue", response_model=AssessmentOutcome)
async def continue_request(
    request_id: UUID,
    session_id: str,
    db: DB,
    gateway: Gateway,
    learner: Learner,
    request: Request,
) -> AssessmentOutcome:
    return await assessment_requests.continue_prepared(
        db, gateway, learner.id, session_id, str(request_id), request.app.state.answer_recovery
    )


class AssessmentRevisionSource(BaseModel):
    attempt_id: str
    root_attempt_id: str
    answer: str
    item: AssessmentView


@router.get("/attempts/{attempt_id}/revision", response_model=AssessmentRevisionSource)
async def revision_source(
    attempt_id: str, session_id: str, db: DB, learner: Learner
) -> AssessmentRevisionSource:
    """Read the learner's submitted answer for deliberate revision; never grade."""
    await ksession.get_owned(db, session_id, learner.id)
    attempt = await db.get(AssessmentAttempt, attempt_id)
    if attempt is None or attempt.learner_id != learner.id or attempt.session_id != session_id:
        raise AppError("revision_original_unavailable", "The submitted answer is unavailable.", 404)
    root_id = attempt.revision_of_attempt_id or attempt.id
    root = await assessment_revisions.validate_root(
        db,
        learner_id=learner.id,
        session_id=session_id,
        assessment_id=attempt.assessment_id,
        root_attempt_id=root_id,
    )
    if attempt.content_fingerprint != root.content_fingerprint:
        raise AppError(
            "revision_content_changed",
            "The submitted answer belongs to another question version.",
            409,
        )
    content = await assessment_content.snapshot(db, attempt.assessment_id, learner.id)
    assessment_content.require_eligible(content)
    if assessment_content.recovery_fingerprint(content) != root.content_fingerprint:
        raise AppError(
            "revision_content_changed",
            "The question changed. Return to your checked feedback.",
            409,
        )
    item = view(assessment_content.assessment(content)).model_copy(
        update={"content_version": assessment_content.token(content)}
    )
    return AssessmentRevisionSource(
        attempt_id=attempt.id,
        root_attempt_id=root.id,
        answer=attempt.answer,
        item=item,
    )
