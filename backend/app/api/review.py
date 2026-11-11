from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query
from pydantic import BaseModel

from app.api.deps import DB, Learner
from app.db.events import EventWriter, Verb
from app.kernel import memory, planner, review_content, review_requests
from app.kernel import session as ksession
from app.schemas.common import ActivityType, Actor, ObjectType
from app.schemas.review import ReviewOut, ReviewRating, ReviewRequestState

router = APIRouter(prefix="/review", tags=["review"])


class ReviewItemOut(BaseModel):
    paired_next_id: str | None = None
    content_version: str
    item_id: str
    assessment_id: str | None = None
    skill_id: str
    skill_title: str
    item_type: str
    question: str
    options: list[str] | None
    reveal: str
    due: str
    state: str


class DueList(BaseModel):
    items: list[ReviewItemOut]
    cap: int
    total_due: int
    as_of: str


def _as_of(value: str | None) -> datetime:
    """Dev/benchmark time travel. Must carry a timezone; naive stamps would corrupt FSRS state."""
    if not value:
        return datetime.now(UTC)
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError("as_of must include a timezone offset, e.g. 2030-01-01T00:00:00+00:00")
    return dt


async def item_view(db: DB, learner_id: str, item_id: str) -> ReviewItemOut:
    content = await review_content.snapshot(db, learner_id, item_id)
    if not content["active"]:
        from app.core.errors import AppError

        raise AppError("not_found", "Review item not found.", 404)
    return ReviewItemOut(
        item_id=content["id"],
        assessment_id=content["assessment_id"],
        skill_id=content["skill_id"],
        skill_title=content["skill_title"] or "",
        item_type=content["item_type"],
        **content["display"],
        due=content["due"] or "",
        state=content["state"] or "new",
        content_version=review_content.content_token(content),
    )


@router.get("/items/{item_id}", response_model=ReviewItemOut)
async def refresh_item(item_id: str, session_id: str, db: DB, learner: Learner) -> ReviewItemOut:
    await ksession.get_owned(db, session_id, learner.id)
    return await item_view(db, learner.id, item_id)


class CorrectionComparison(BaseModel):
    earlier: str
    corrected: str


@router.get("/items/{item_id}/correction", response_model=CorrectionComparison | None)
async def earlier_correction(
    item_id: str, session_id: str, content_version: str, db: DB, learner: Learner
) -> CorrectionComparison | None:
    """After recall, compare the latest independently checked answer with its linked revision."""
    from sqlalchemy import select

    from app.db.models import AssessmentAttempt
    from app.kernel.correction_validation import option_index
    from app.orchestrator import assessment_content

    session = await ksession.get_owned(db, session_id, learner.id)
    view = await item_view(db, learner.id, item_id)
    if view.content_version != content_version or not view.assessment_id or not view.options:
        return None
    assessment = await assessment_content.snapshot(db, view.assessment_id, learner.id)
    if assessment["kind"] != "mcq":
        return None
    fingerprint = assessment_content.recovery_fingerprint(assessment)
    attempts = (
        select(AssessmentAttempt)
        .where(
            AssessmentAttempt.learner_id == learner.id,
            AssessmentAttempt.assessment_id == view.assessment_id,
        )
        .order_by(AssessmentAttempt.ts.desc(), AssessmentAttempt.id.desc())
        .limit(1)
    )
    original = await db.scalar(attempts.where(AssessmentAttempt.revision_of_attempt_id.is_(None)))
    if (
        not original
        or original.correct is not False
        or (original.confidence_pre or 0) < 4
        or original.content_fingerprint != fingerprint
        or original.grader_route != "deterministic"
        or not original.session_id
        or original.session_id == session_id
    ):
        return None
    revision = await db.scalar(
        attempts.where(AssessmentAttempt.revision_of_attempt_id == original.id)
    )
    if (
        not revision
        or revision.correct is not True
        or revision.content_fingerprint != fingerprint
        or revision.grader_route != "deterministic"
        or revision.session_id != original.session_id
        or revision.ts >= session.started_at
    ):
        return None

    def display(answer: str) -> str:
        index = option_index(answer.strip(), len(view.options or []))
        return view.options[index] if view.options and index is not None else answer

    return CorrectionComparison(
        earlier=display(original.answer), corrected=display(revision.answer)
    )


@router.get(
    "/due",
    summary="Due review items, capped to the minimum-viable review for this session",
    response_model=DueList,
)
async def due(
    db: DB,
    learner: Learner,
    session_id: str = Query(...),
    as_of: str | None = Query(None, description="ISO time; dev/benchmark time travel"),
    all: bool = Query(False, description="Undo the minimum-viable cap for this call"),
    domain: str | None = Query(
        None, description="only this domain (e.g. language); default: all but language"
    ),
) -> DueList:
    s = await ksession.get_owned(db, session_id, learner.id)
    now = _as_of(as_of)
    cap = memory.review_cap(s.mode, s.energy)
    maintenance = planner.is_maintenance_plan(s.planned_blocks_json or [])
    if maintenance:
        cap = min(cap, 3)
    cp = await ksession.load_checkpoint(db, s.id) or {}
    all_due = await memory.due_items(
        db,
        learner.id,
        now=now,
        cap=500,
        domain=domain,
        skill_ids=cp.get("scope_skill_ids") if domain is None else None,
        exclude_domains=() if domain else ("language",),  # AI/ML review never mixes vocab in
    )
    if all:
        cap = max(cap, len(all_due))
    elif len(all_due) > cap:
        await EventWriter(db, ksession.event_context(s, activity=ActivityType.RETRIEVAL)).emit(
            Verb.ADAPTED,
            ObjectType.SESSION,
            s.id,
            actor=Actor.SYSTEM,
            context={
                "what": f"review_cap={cap}",
                "why": "explicit maintenance plan"
                if maintenance
                else f"mode={s.mode} energy={s.energy}",
                "reversible": True,
                "policy_version": "planner.maintenance.v1" if maintenance else "v1",
            },
        )
    admitted = all_due[:cap]
    paired_next: dict[str, str] = {}
    if (
        domain != "language"
        and cp.get("block_type") == "interleaved_review"
        and cp.get("block_status") == "running"
    ):
        from app.kernel.discrimination_review import group_due_pairs

        admitted, paired_next = group_due_pairs(admitted)
    items = []
    for item, _ in admitted:
        view = await item_view(db, learner.id, item.id)
        view.paired_next_id = paired_next.get(item.id)
        items.append(view)
    return DueList(items=items, cap=cap, total_due=len(all_due), as_of=now.isoformat())


@router.get(
    "/requests/{request_id}",
    summary="Read a review rating result without changing its schedule",
    response_model=ReviewRequestState,
)
async def request_result(
    request_id: UUID, session_id: str, db: DB, learner: Learner
) -> ReviewRequestState:
    return await review_requests.lookup(db, learner.id, session_id, str(request_id))


@router.post("/{item_id}", summary="Rate a recalled item 1-4 (FSRS)", response_model=ReviewOut)
async def rate(
    item_id: str,
    body: ReviewRating,
    db: DB,
    learner: Learner,
    as_of: str | None = Query(None),
    idempotency_key: Annotated[UUID | None, Header()] = None,
) -> ReviewOut:
    return await review_requests.submit(
        db,
        learner.id,
        item_id,
        body,
        now=_as_of(as_of),
        as_of=as_of,
        identity=str(idempotency_key) if idempotency_key is not None else None,
    )
