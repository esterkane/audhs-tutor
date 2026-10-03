"""Owned review requests: one atomic FSRS/event/outcome write set, no model calls."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db import workspace_requests
from app.db.events import EventWriter
from app.db.models import MemoryState, ReviewItem, WorkspaceRequest
from app.kernel import memory
from app.kernel import session as ksession
from app.schemas.common import ActivityType
from app.schemas.review import ReviewOut, ReviewRating, ReviewRequestState


async def submit(
    db: AsyncSession,
    learner_id: str,
    item_id: str,
    body: ReviewRating,
    *,
    now: datetime,
    as_of: str | None,
    identity: str | None,
) -> ReviewOut:
    session = await ksession.get_owned(db, body.session_id, learner_id)
    item = await db.scalar(
        select(ReviewItem).where(
            ReviewItem.id == item_id,
            ReviewItem.learner_id == learner_id,
        )
    )
    if item is None:
        raise AppError("not_found", "Review item not found.", 404)
    claim_id = None
    if identity is not None:
        claim_id, saved = await workspace_requests.claim(
            db,
            learner_id,
            session.id,
            f"review:{identity}",
            {"item_id": item_id, "body": body.model_dump(mode="json"), "as_of": as_of},
        )
        if saved is not None:
            return ReviewOut.model_validate(saved)
    try:
        # Acquire SQLite's write lock before reading the mutable card: distinct concurrent
        # requests must not both calculate their next state from the same earlier snapshot.
        from sqlalchemy import update

        await db.execute(
            update(MemoryState)
            .where(
                MemoryState.review_item_id == item_id,
                MemoryState.learner_id == learner_id,
            )
            .values(due=MemoryState.due)
        )
        events = EventWriter(db, ksession.event_context(session, activity=ActivityType.RETRIEVAL))
        log = await memory.review(
            db,
            learner_id,
            item_id,
            min(body.rating, 2) if body.hint_count else body.rating,
            now=now if as_of is not None else datetime.now(UTC),
            latency_ms=body.latency_ms,
            events=events,
            confidence_pre=body.confidence_pre,
            hint_count=body.hint_count,
            commit=False,
        )
        state = await db.scalar(
            select(MemoryState).where(
                MemoryState.review_item_id == item_id,
                MemoryState.learner_id == learner_id,
            )
        )
        assert state is not None
        result = ReviewOut(
            item_id=item_id,
            due=state.due,
            state=state.state,
            stability=state.stability,
            predicted_retrievability=log.predicted_retrievability,
        )
        if claim_id is not None:
            await workspace_requests.complete(
                db, learner_id, claim_id, result.model_dump(mode="json"), commit=False
            )
        await db.commit()
        return result
    except BaseException:
        await db.rollback()
        raise


async def lookup(
    db: AsyncSession, learner_id: str, session_id: str, identity: str
) -> ReviewRequestState:
    await ksession.get_owned(db, session_id, learner_id)
    row = await db.scalar(
        select(WorkspaceRequest).where(
            WorkspaceRequest.learner_id == learner_id,
            WorkspaceRequest.session_id == session_id,
            WorkspaceRequest.request_key == f"review:{identity}",
        )
    )
    if row is None:
        return ReviewRequestState(status="not_found")
    if row.response_json is None:
        return ReviewRequestState(status="unresolved")
    return ReviewRequestState(
        status="completed", result=ReviewOut.model_validate(row.response_json)
    )
