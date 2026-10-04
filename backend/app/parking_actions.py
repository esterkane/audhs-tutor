"""Short serialized reminder transactions; never learner competency changes."""

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.base import new_id
from app.db.events import EventContext, EventWriter, Verb
from app.db.models import ParkingLotItem, SkillNode, ThoughtAction
from app.schemas.common import Mode, ObjectType


class ThoughtActionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_key: str = Field(min_length=1, max_length=128)
    expected_revision: int = Field(ge=0)
    action: Literal["promote", "drop", "undo"]
    promoted_to: str = Field(default="next_session", min_length=1, max_length=128)
    undo_of: str | None = Field(default=None, min_length=1, max_length=128)


def state(item: ParkingLotItem) -> dict[str, str | None]:
    return {"status": item.status, "node_id": item.node_id, "promoted_to": item.promoted_to}


async def apply_action(
    db: AsyncSession,
    learner_id: str,
    item_id: str,
    body: ThoughtActionIn,
    *,
    legacy: bool = False,
) -> tuple[ParkingLotItem, ThoughtAction]:
    fingerprint = hashlib.sha256(
        json.dumps(
            {"item_id": item_id, **body.model_dump(exclude={"request_key"})}, sort_keys=True
        ).encode()
    ).hexdigest()
    # Finish dependency reads, then serialize the complete check/write/audit transaction.
    await db.commit()
    await db.execute(text("BEGIN IMMEDIATE"))
    item = await db.scalar(
        select(ParkingLotItem)
        .where(ParkingLotItem.id == item_id, ParkingLotItem.learner_id == learner_id)
        .execution_options(populate_existing=True)
    )
    if item is None:
        raise AppError("not_found", "Thought not found.", 404)
    prior = await db.scalar(
        select(ThoughtAction).where(
            ThoughtAction.learner_id == learner_id, ThoughtAction.request_key == body.request_key
        )
    )
    if prior:
        if prior.fingerprint != fingerprint:
            raise AppError(
                "request_conflict", "This action identity belongs to another request.", 409
            )
        await db.commit()
        return item, prior
    if not legacy and item.revision != body.expected_revision:
        raise AppError(
            "revision_conflict",
            "This thought has changed. Refresh before choosing another action.",
            409,
        )
    before = state(item)
    if body.action == "undo":
        original = await db.get(ThoughtAction, body.undo_of) if body.undo_of else None
        if original is None or original.learner_id != learner_id or original.item_id != item_id:
            raise AppError("not_found", "Original action not found.", 404)
        if (
            original.action == "undo"
            or original.revision != item.revision
            or original.after_json != before
        ):
            raise AppError(
                "revision_conflict", "A newer change prevents this undo. Refresh the thought.", 409
            )
        target = original.before_json
        if target["node_id"] and await db.get(SkillNode, target["node_id"]) is None:
            raise AppError("revision_conflict", "The previous skill link no longer exists.", 409)
        item.status = target["status"]
        item.node_id = target["node_id"]
        item.promoted_to = target["promoted_to"]
    elif body.action == "drop":
        item.status = "dropped"
    else:
        if item.status == "dropped":
            raise AppError(
                "revision_conflict", "This thought was removed. Undo its removal first.", 409
            )
        if body.promoted_to != "next_session":
            node = await db.get(SkillNode, body.promoted_to)
            if node is None:
                raise AppError("not_found", "Skill not found.", 404)
            item.node_id = node.id
        item.status, item.promoted_to = "promoted", body.promoted_to
    item.revision += 1
    receipt = ThoughtAction(
        id=new_id(),
        learner_id=learner_id,
        item_id=item.id,
        request_key=body.request_key,
        fingerprint=fingerprint,
        action=body.action,
        before_json=before,
        after_json=state(item),
        revision=item.revision,
        undo_of=body.undo_of,
    )
    db.add(receipt)
    await db.flush()
    ctx = EventContext(learner_id=learner_id, session_id=None, mode=Mode.STEADY, energy=3)
    if body.action == "promote":
        await EventWriter(db, ctx).emit(
            Verb.PROMOTED,
            ObjectType.NOTE,
            item.id,
            context={"node_id": item.node_id, "promoted_to": item.promoted_to},
        )
    else:
        await EventWriter(db, ctx).emit(
            Verb.THOUGHT_CHANGED,
            ObjectType.NOTE,
            item.id,
            context={
                "action_id": receipt.id,
                "action": body.action,
                "revision": item.revision,
                "undo_of": body.undo_of,
            },
        )
    return item, receipt
