from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query
from pydantic import BaseModel

from app.api.deps import DB, Learner
from app.db.events import EventWriter, Verb
from app.kernel import memory, review_content, review_requests
from app.kernel import session as ksession
from app.schemas.common import ActivityType, Actor, ObjectType
from app.schemas.review import ReviewOut, ReviewRating, ReviewRequestState

router = APIRouter(prefix="/review", tags=["review"])


class ReviewItemOut(BaseModel):
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
                "why": f"mode={s.mode} energy={s.energy}",
                "reversible": True,
                "policy_version": "v1",
            },
        )
    items = []
    for item, _ in all_due[:cap]:
        items.append(await item_view(db, learner.id, item.id))
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
