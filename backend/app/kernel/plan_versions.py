"""Exact session-plan bindings; sub-phase and soft-timer changes do not replace a plan."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models import Session
from app.kernel import session as ksession


async def binding(db: AsyncSession, session: Session) -> dict[str, Any]:
    cp = await ksession.load_checkpoint(db, session.id) or {}
    return {
        "version": 1,
        "session_id": session.id,
        "plan": session.planned_blocks_json or [],
        "plan_version": cp.get("plan_version", 1),
        "block_index": cp.get("block_index"),
        "block_status": cp.get("block_status"),
        "energy": session.energy,
    }


def protected_count(snapshot: dict[str, Any]) -> int:
    index = snapshot.get("block_index")
    return index + 1 if isinstance(index, int) and index >= 0 else 0


async def require_current(db: AsyncSession, session: Session, expected: Any) -> dict[str, Any]:
    current = await binding(db, session)
    if not isinstance(expected, dict) or expected != current:
        raise AppError(
            "stale_plan",
            "The session has changed. Your current activity is kept. Review an updated plan before applying changes.",
            http_status=409,
        )
    return current
