"""Session plans and blocks (planner-v1). Blocks are the only boundaries for domain switches."""

from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.api.deps import DB, Learner
from app.db.events import EventWriter, Verb
from app.db.models import Session
from app.kernel import competency, memory, planner, preferences, skill_graph
from app.kernel import session as ksession
from app.schemas.common import ActivityType, ObjectType

router = APIRouter(prefix="/plan", tags=["plan"])


async def build_plan(db: DB, learner_id: str, mode: str, energy: int) -> planner.Plan:
    nxt = await skill_graph.next_skill(db, learner_id)
    due = await memory.due_items(db, learner_id, cap=100)
    return planner.plan_session(
        planner.PlanInput(
            mode=mode,
            energy=energy,
            due_reviews=len(due),
            next_skill_id=nxt.id if nxt else None,
            next_skill_mastery=await competency.mastery(db, learner_id, nxt.id) if nxt else 0.0,
            review_node_ids=sorted({item.skill_id for item, _ in due}),
            preferences=await preferences.get_all(db, learner_id),
        )
    )


@router.get(
    "/preview",
    summary="Plan for a mode/energy before starting a session",
    response_model=planner.Plan,
)
async def preview(
    db: DB, learner: Learner, mode: str = Query("steady"), energy: int = Query(3, ge=1, le=5)
) -> planner.Plan:
    return await build_plan(db, learner.id, mode, energy)


class BlockEvent(BaseModel):
    session_id: str
    index: int = Field(ge=0)
    actual_min: float | None = None
    switched_early: bool = False
    reason: str | None = None
    grasp_passed: bool | None = None


class BlockOut(BaseModel):
    index: int
    block: planner.Block
    allowed: bool
    message: str
    next_index: int | None


def _blocks(s: Session) -> list[planner.Block]:
    return [planner.Block.model_validate(b) for b in (s.planned_blocks_json or [])]


@router.post(
    "/blocks/start", summary="Start a planned block (emits block_started)", response_model=BlockOut
)
async def start_block(body: BlockEvent, db: DB) -> BlockOut:
    s = await ksession.get(db, body.session_id)
    blocks = _blocks(s)
    if body.index >= len(blocks):
        raise KeyError("block index out of range")
    b = blocks[body.index]
    events = EventWriter(db, ksession.event_context(s, activity=_activity(b.type)))
    await events.emit(
        Verb.BLOCK_STARTED,
        ObjectType.BLOCK,
        f"{s.id}:{body.index}",
        context={"block_type": b.type, "planned_min": b.planned_min, "node_ids": b.node_ids},
    )
    cp = await ksession.load_checkpoint(db, s.id) or {}
    await ksession.save_checkpoint(
        db, s, {**cp, "block_index": body.index, "phase": _phase(b.type)}
    )
    return BlockOut(
        index=body.index,
        block=b,
        allowed=True,
        message="started",
        next_index=body.index + 1 if body.index + 1 < len(blocks) else None,
    )


@router.post(
    "/blocks/end",
    summary="End a block; early switches out of new material need a grasp check",
    response_model=BlockOut,
)
async def end_block(body: BlockEvent, db: DB) -> BlockOut:
    s = await ksession.get(db, body.session_id)
    blocks = _blocks(s)
    if body.index >= len(blocks):
        raise KeyError("block index out of range")
    b = blocks[body.index]
    if body.switched_early:
        ok, why = planner.can_switch_early(
            b, grasp_passed=body.grasp_passed, reason=body.reason or ""
        )
        if not ok:
            return BlockOut(index=body.index, block=b, allowed=False, message=why, next_index=None)
    events = EventWriter(db, ksession.event_context(s, activity=_activity(b.type)))
    await events.emit(
        Verb.BLOCK_ENDED,
        ObjectType.BLOCK,
        f"{s.id}:{body.index}",
        result={
            "actual_min": body.actual_min,
            "switched_early": body.switched_early,
            "reason": body.reason,
        },
        context={"block_type": b.type, "planned_min": b.planned_min, "node_ids": b.node_ids},
    )
    nxt = body.index + 1 if body.index + 1 < len(blocks) else None
    return BlockOut(index=body.index, block=b, allowed=True, message="ended", next_index=nxt)


def _activity(block_type: str) -> ActivityType:
    return {
        "movement_primer": ActivityType.MOVEMENT,
        "retrieval": ActivityType.RETRIEVAL,
        "new_material": ActivityType.NEW_MATERIAL,
        "challenge": ActivityType.CHALLENGE,
        "interleaved_review": ActivityType.INTERLEAVED_REVIEW,
        "domain_switch": ActivityType.DOMAIN_SWITCH,
        "recap": ActivityType.RECAP,
    }.get(block_type, ActivityType.CHAT)


def _phase(block_type: str) -> str:
    return {
        "retrieval": "review",
        "interleaved_review": "review",
        "new_material": "teach",
        "challenge": "challenge",
        "recap": "recap",
    }.get(block_type, "teach")


def plan_to_json(plan: planner.Plan) -> list[dict[str, Any]]:
    return [b.model_dump() for b in plan.blocks]
