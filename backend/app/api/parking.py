from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import DB, Learner
from app.db.events import EventContext, EventWriter, Verb
from app.db.models import ParkingLotItem, SkillNode
from app.kernel import session as ksession
from app.orchestrator.tools import park_tangent
from app.schemas.common import Mode, ObjectType

router = APIRouter(prefix="/parking", tags=["parking"])


class ParkIn(BaseModel):
    session_id: str | None = None
    text: str = Field(min_length=1, max_length=500)
    node_id: str | None = None


class ParkOut(BaseModel):
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
    if body.session_id:
        s = await ksession.get(db, body.session_id)
        events = EventWriter(db, ksession.event_context(s))
        return _out(await park_tangent(db, s, body.text, node_id=body.node_id, events=events))
    item = ParkingLotItem(
        learner_id=learner.id, session_id=None, text=body.text, node_id=body.node_id
    )
    db.add(item)
    await db.commit()
    ctx = EventContext(learner_id=learner.id, session_id=None, mode=Mode.STEADY, energy=3)
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


async def _item(db: DB, learner_id: str, item_id: str) -> ParkingLotItem:
    item = await db.get(ParkingLotItem, item_id)
    if item is None or item.learner_id != learner_id:
        raise KeyError(item_id)
    return item


@router.post(
    "/{item_id}/promote",
    summary="Promote a parked tangent: to the next session (Home reminder) or onto a skill node",
    response_model=ParkOut,
)
async def promote(item_id: str, body: PromoteIn, db: DB, learner: Learner) -> ParkOut:
    item = await _item(db, learner.id, item_id)
    if item.status == "dropped":
        raise ValueError("this item was dropped; park it again if you want it back")
    if body.promoted_to != "next_session":
        node = await db.get(SkillNode, body.promoted_to)
        if node is None:
            raise KeyError(body.promoted_to)
        item.node_id = node.id
    item.status, item.promoted_to = "promoted", body.promoted_to
    await db.commit()
    ctx = EventContext(learner_id=learner.id, session_id=None, mode=Mode.STEADY, energy=3)
    await EventWriter(db, ctx).emit(
        Verb.PROMOTED,
        ObjectType.NOTE,
        item.id,
        context={"node_id": item.node_id, "promoted_to": body.promoted_to},
    )
    return _out(item)


@router.post("/{item_id}/drop", summary="Drop a parked or promoted item", response_model=ParkOut)
async def drop(item_id: str, db: DB, learner: Learner) -> ParkOut:
    item = await _item(db, learner.id, item_id)
    item.status = "dropped"
    await db.commit()
    return _out(item)
