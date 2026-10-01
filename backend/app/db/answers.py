"""Immutable completed-answer snapshots; no generation, grading or corpus indexing.

The caller finishes prior trace/event transactions first. This function owns its short
insert transaction. Turn deduplication is not request-level exactly-once inference.
"""

import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import new_id, utcnow_iso
from app.db.models import TutorAnswer
from app.kernel.session import get_owned


async def save_completed(
    db: AsyncSession,
    *,
    learner_id: str,
    session_id: str,
    turn_id: str,
    surface: str,
    request: dict[str, Any],
    text: str,
    metadata: dict[str, Any],
) -> TutorAnswer:
    await get_owned(db, session_id, learner_id)
    if not text.strip():
        raise ValueError("An empty answer cannot be saved as complete")
    payload = {
        "session_id": session_id,
        "surface": surface,
        "request": request,
        "text": text,
        "metadata": metadata,
    }
    fingerprint = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    try:
        await db.execute(
            insert(TutorAnswer)
            .values(
                id=new_id(),
                learner_id=learner_id,
                session_id=session_id,
                turn_id=turn_id,
                surface=surface,
                request_json=request,
                text=text,
                metadata_json=metadata,
                fingerprint=fingerprint,
                created_at=utcnow_iso(),
            )
            .on_conflict_do_nothing(index_elements=["learner_id", "turn_id"])
        )
        row = (
            await db.execute(
                select(TutorAnswer).where(
                    TutorAnswer.learner_id == learner_id,
                    TutorAnswer.turn_id == turn_id,
                )
            )
        ).scalar_one()
        if row.fingerprint != fingerprint:
            raise ValueError("This turn already has a different saved answer")
        await db.commit()
        return row
    except BaseException:
        await db.rollback()
        raise
