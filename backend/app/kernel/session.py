"""Sessions, checkpoints and the EventContext every event is stamped with."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.base import utcnow_iso
from app.db.events import EventContext, EventWriter, Verb
from app.db.models import Session, SessionCheckpoint
from app.schemas.common import ActivityType, Domain, Mode, ObjectType

CHECKPOINT_TTL_DAYS = 7


def event_context(
    session: Session,
    *,
    domain: Domain = Domain.AI_ML,
    activity: ActivityType = ActivityType.NEW_MATERIAL,
) -> EventContext:
    return EventContext(
        learner_id=session.learner_id,
        session_id=session.id,
        mode=Mode(session.mode),
        energy=session.energy,
        socratic=session.socratic,
        experiment_arm=session.experiment_arm_id,
        domain=domain,
        activity_type=activity,
    )


async def start(
    db: AsyncSession,
    learner_id: str,
    *,
    mode: Mode,
    energy: int,
    socratic: bool = False,
    planned_blocks: list[str] | None = None,
    emit: bool = True,
) -> Session:
    """Create the session row; `emit=False` lets the caller finish set-up (experiment arm, plan)
    before the single `started` event is written with `emit_started`."""
    if not 1 <= energy <= 5:
        raise ValueError("energy must be 1-5")
    s = Session(
        learner_id=learner_id,
        mode=str(mode),
        energy=energy,
        socratic=socratic,
        planned_blocks_json=planned_blocks or [],
    )
    db.add(s)
    await db.commit()
    if emit:
        await emit_started(db, s, planned_blocks or [])
    return s


async def emit_started(db: AsyncSession, s: Session, planned_blocks: list[str]) -> None:
    await EventWriter(db, event_context(s, domain=Domain.META, activity=ActivityType.CHAT)).emit(
        Verb.STARTED, ObjectType.SESSION, s.id, context={"planned_blocks": planned_blocks}
    )


async def get(db: AsyncSession, session_id: str) -> Session:
    s = await db.get(Session, session_id)
    if s is None:
        raise KeyError(f"session {session_id!r} not found")
    return s


async def get_owned(db: AsyncSession, session_id: str, learner_id: str) -> Session:
    """Resolve a session without revealing whether another learner owns it."""
    s = await db.scalar(
        select(Session).where(Session.id == session_id, Session.learner_id == learner_id)
    )
    if s is None:
        raise KeyError("session not found")
    return s


async def lock_for_transition(db: AsyncSession, session_id: str, learner_id: str) -> Session:
    """Serialize session transition preparation across SQLite writers without changing learner state.

    The caller owns commit/rollback. Refresh after acquiring the write lock so a
    second worker observes the first worker's completed transaction.
    """
    await db.execute(
        update(Session)
        .where(Session.id == session_id, Session.learner_id == learner_id)
        .values(ended_at=Session.ended_at)
        .execution_options(synchronize_session=False)
    )
    s = await db.get(Session, session_id, populate_existing=True)
    if s is None or s.learner_id != learner_id:
        raise KeyError("session not found")
    return s


@asynccontextmanager
async def open_transition(
    db: AsyncSession, session_id: str, learner_id: str
) -> AsyncIterator[Session]:
    """Own a short, local open-session mutation; inner writers must defer commits."""
    try:
        s = await lock_for_transition(db, session_id, learner_id)
        if s.ended_at is not None:
            raise AppError(
                "session_ended", "This session has ended. Return Home to continue.", http_status=409
            )
        yield s
        await db.commit()
    except BaseException:
        await db.rollback()
        raise


async def end(
    db: AsyncSession,
    session_id: str,
    *,
    energy_after: int | None,
    self_report: int | None,
    notes: str | None = None,
) -> Session:
    """Own the end-state/recap transaction; concurrent retries preserve the first completion.

    API callers may stage block cleanup and recall scheduling in this same transaction.
    """
    try:
        won = await db.scalar(
            update(Session)
            .where(Session.id == session_id, Session.ended_at.is_(None))
            .values(ended_at=utcnow_iso(), energy_after=energy_after)
            .returning(Session.id)
            .execution_options(synchronize_session=False)
        )
        s = await db.get(Session, session_id, populate_existing=True)
        if s is None:
            raise KeyError(f"session {session_id!r} not found")
        if won is not None:
            await EventWriter(
                db, event_context(s, domain=Domain.META, activity=ActivityType.RECAP)
            ).emit(
                Verb.ENDED,
                ObjectType.SESSION,
                s.id,
                result={"energy_after": energy_after, "self_report": self_report, "notes": notes},
                commit=False,
            )
        await db.commit()
        return s
    except BaseException:
        await db.rollback()
        raise


async def save_checkpoint(
    db: AsyncSession, session: Session, packet: dict[str, Any], *, commit: bool = True
) -> SessionCheckpoint:
    """One row per session, updated in place (the checkpoint is a resume point, not an audit
    store). `commit=False` lets a caller commit it together with the event it belongs to."""
    cp = (
        await db.execute(
            select(SessionCheckpoint)
            .where(SessionCheckpoint.session_id == session.id)
            .order_by(SessionCheckpoint.ts.desc(), SessionCheckpoint.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    expires = (datetime.now(UTC) + timedelta(days=CHECKPOINT_TTL_DAYS)).isoformat(
        timespec="milliseconds"
    )
    if cp is None:
        cp = SessionCheckpoint(
            learner_id=session.learner_id,
            session_id=session.id,
            packet_json=packet,
            expires_at=expires,
        )
        db.add(cp)
    else:
        cp.packet_json = packet
        cp.ts = utcnow_iso()
        cp.expires_at = expires
    if commit:
        await db.commit()
    else:
        await db.flush()
    return cp


async def prune_checkpoints(
    db: AsyncSession, session_id: str, *, keep: int = 1, commit: bool = True
) -> int:
    """Remove older duplicate rows (pre-P1 sessions could have several); newest `keep` stay."""
    rows = list(
        (
            await db.execute(
                select(SessionCheckpoint)
                .where(SessionCheckpoint.session_id == session_id)
                .order_by(SessionCheckpoint.ts.desc(), SessionCheckpoint.id.desc())
            )
        ).scalars()
    )
    n = 0
    for cp in rows[keep:]:
        await db.delete(cp)
        n += 1
    if n:
        if commit:
            await db.commit()
        else:
            await db.flush()
    return n


async def load_checkpoint(db: AsyncSession, session_id: str) -> dict[str, Any] | None:
    stmt = (
        select(SessionCheckpoint)
        .where(
            SessionCheckpoint.session_id == session_id, SessionCheckpoint.expires_at > utcnow_iso()
        )
        .order_by(SessionCheckpoint.ts.desc(), SessionCheckpoint.id.desc())
        .limit(1)
    )
    cp = (await db.execute(stmt)).scalar_one_or_none()
    return cp.packet_json if cp else None
