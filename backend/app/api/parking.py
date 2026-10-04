import hashlib
import json

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field, TypeAdapter
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert

from app.api.deps import DB, Learner
from app.core.errors import AppError
from app.db.base import new_id
from app.db.events import EventContext, EventWriter, Verb
from app.db.models import ParkingLotItem
from app.kernel import session as ksession
from app.parking_actions import ThoughtActionIn, apply_action
from app.schemas.capture_context import CaptureContext
from app.schemas.common import Mode, ObjectType

router = APIRouter(prefix="/parking", tags=["parking"])


class ParkIn(BaseModel):
    original_context: CaptureContext | None = None
    request_key: str | None = Field(default=None, min_length=1, max_length=128)
    session_id: str | None = None
    text: str = Field(min_length=1, max_length=500)
    node_id: str | None = None


class ParkOut(BaseModel):
    revision: int = 0
    original_context: CaptureContext | None = None
    id: str
    text: str
    node_id: str | None
    status: str
    promoted_to: str | None = None
    created_at: str


class ParkList(BaseModel):
    items: list[ParkOut]


def _out(p: ParkingLotItem) -> ParkOut:
    return ParkOut(
        revision=p.revision,
        original_context=(
            TypeAdapter(CaptureContext).validate_python(p.original_context_json)
            if p.original_context_json
            else None
        ),
        id=p.id,
        text=p.text,
        node_id=p.node_id,
        status=p.status,
        promoted_to=p.promoted_to,
        created_at=p.created_at,
    )


@router.post(
    "",
    summary="Park a tangent (≤ 2 interactions, linked to the current node)",
    response_model=ParkOut,
    status_code=201,
)
async def park(body: ParkIn, db: DB, learner: Learner) -> ParkOut:
    context = body.original_context.model_dump() if body.original_context else None
    if body.request_key is not None:
        ctx = EventContext(learner_id=learner.id, session_id=None, mode=Mode.STEADY, energy=3)
        if body.session_id:
            session = await ksession.get_owned(db, body.session_id, learner.id)
            ctx = ksession.event_context(session)
        fingerprint = hashlib.sha256(
            json.dumps(
                body.model_dump(
                    exclude={"request_key"} | ({"original_context"} if context is None else set())
                ),
                sort_keys=True,
            ).encode()
        ).hexdigest()
        # End dependency reads before the insert acquires SQLite's write lock.
        # A duplicate waits for the first short item/event transaction to finish.
        await db.commit()
        identity = new_id()
        inserted = await db.scalar(
            insert(ParkingLotItem)
            .values(
                id=identity,
                learner_id=learner.id,
                session_id=body.session_id,
                text=body.text,
                node_id=body.node_id,
                request_key=body.request_key,
                request_fingerprint=fingerprint,
                original_context_json=context,
            )
            .on_conflict_do_nothing(index_elements=["learner_id", "request_key"])
            .returning(ParkingLotItem.id)
        )
        item = await db.scalar(
            select(ParkingLotItem).where(
                ParkingLotItem.learner_id == learner.id,
                ParkingLotItem.request_key == body.request_key,
            )
        )
        assert item is not None
        if item.request_fingerprint != fingerprint:
            raise AppError(
                "request_conflict", "This save identity belongs to different text or context.", 409
            )
        if inserted:
            await EventWriter(db, ctx).emit(
                Verb.PARKED, ObjectType.NOTE, item.id, context={"node_id": body.node_id}
            )
        else:
            await db.commit()
        return _out(item)
    ctx = EventContext(learner_id=learner.id, session_id=None, mode=Mode.STEADY, energy=3)
    if body.session_id:
        session = await ksession.get_owned(db, body.session_id, learner.id)
        ctx = ksession.event_context(session)
    item = ParkingLotItem(
        learner_id=learner.id,
        session_id=body.session_id,
        text=body.text,
        node_id=body.node_id,
        original_context_json=context,
    )
    db.add(item)
    await db.flush()
    await EventWriter(db, ctx).emit(
        Verb.PARKED, ObjectType.NOTE, item.id, context={"node_id": body.node_id}
    )
    return _out(item)


@router.get("", summary="Parked items", response_model=ParkList)
async def list_parked(db: DB, learner: Learner, status: str = Query("parked")) -> ParkList:
    stmt = (
        select(ParkingLotItem)
        .where(ParkingLotItem.learner_id == learner.id, ParkingLotItem.status == status)
        .order_by(ParkingLotItem.created_at.desc())
    )
    return ParkList(items=[_out(p) for p in (await db.execute(stmt)).scalars()])


class PromoteIn(BaseModel):
    promoted_to: str = Field(
        default="next_session",
        description="'next_session' (shown on Home until done) or a skill node id",
    )


class ThoughtActionOut(BaseModel):
    item: ParkOut
    action_id: str
    action_revision: int
    can_undo: bool


@router.post("/{item_id}/actions", response_model=ThoughtActionOut)
async def change_thought(
    item_id: str, body: ThoughtActionIn, db: DB, learner: Learner
) -> ThoughtActionOut:
    item, receipt = await apply_action(db, learner.id, item_id, body)
    return ThoughtActionOut(
        item=_out(item),
        action_id=receipt.id,
        action_revision=receipt.revision,
        can_undo=receipt.action != "undo" and receipt.revision == item.revision,
    )


@router.post("/{item_id}/promote", response_model=ParkOut)
async def promote(item_id: str, body: PromoteIn, db: DB, learner: Learner) -> ParkOut:
    item, _ = await apply_action(
        db,
        learner.id,
        item_id,
        ThoughtActionIn(
            request_key=new_id(),
            expected_revision=0,
            action="promote",
            promoted_to=body.promoted_to,
        ),
        legacy=True,
    )
    return _out(item)


@router.post("/{item_id}/drop", response_model=ParkOut)
async def drop(item_id: str, db: DB, learner: Learner) -> ParkOut:
    item, _ = await apply_action(
        db,
        learner.id,
        item_id,
        ThoughtActionIn(
            request_key=new_id(),
            expected_revision=0,
            action="drop",
        ),
        legacy=True,
    )
    return _out(item)
