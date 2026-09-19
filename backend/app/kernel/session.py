"""Sessions, checkpoints and the EventContext every event is stamped with."""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
) -> Session:
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
    await EventWriter(db, event_context(s, domain=Domain.META, activity=ActivityType.CHAT)).emit(
        Verb.STARTED, ObjectType.SESSION, s.id, context={"planned_blocks": planned_blocks or []}
    )
    return s


async def get(db: AsyncSession, session_id: str) -> Session:
    s = await db.get(Session, session_id)
    if s is None:
        raise KeyError(f"session {session_id!r} not found")
    return s


async def end(
    db: AsyncSession,
    session_id: str,
    *,
    energy_after: int,
    self_report: int,
    notes: str | None = None,
) -> Session:
    s = await get(db, session_id)
    if s.ended_at:
        return s
    s.ended_at = utcnow_iso()
    s.energy_after = energy_after
    await db.commit()
    await EventWriter(db, event_context(s, domain=Domain.META, activity=ActivityType.RECAP)).emit(
        Verb.ENDED,
        ObjectType.SESSION,
        s.id,
        result={"energy_after": energy_after, "self_report": self_report, "notes": notes},
    )
    return s


async def save_checkpoint(
    db: AsyncSession, session: Session, packet: dict[str, Any]
) -> SessionCheckpoint:
    cp = SessionCheckpoint(
        learner_id=session.learner_id,
        session_id=session.id,
        packet_json=packet,
        expires_at=(datetime.now(UTC) + timedelta(days=CHECKPOINT_TTL_DAYS)).isoformat(
            timespec="milliseconds"
        ),
    )
    db.add(cp)
    await db.commit()
    return cp


async def prune_checkpoints(db: AsyncSession, session_id: str, *, keep: int = 1) -> int:
    """Keep only the newest `keep` checkpoints of a session; they are not an audit store."""
    rows = list(
        (
            await db.execute(
                select(SessionCheckpoint)
                .where(SessionCheckpoint.session_id == session_id)
                .order_by(SessionCheckpoint.ts.desc())
            )
        ).scalars()
    )
    n = 0
    for cp in rows[keep:]:
        await db.delete(cp)
        n += 1
    await db.commit()
    return n


async def load_checkpoint(db: AsyncSession, session_id: str) -> dict[str, Any] | None:
    stmt = (
        select(SessionCheckpoint)
        .where(
            SessionCheckpoint.session_id == session_id, SessionCheckpoint.expires_at > utcnow_iso()
        )
        .order_by(SessionCheckpoint.ts.desc())
        .limit(1)
    )
    cp = (await db.execute(stmt)).scalar_one_or_none()
    return cp.packet_json if cp else None
