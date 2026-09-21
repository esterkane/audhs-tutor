"""Session plans and blocks (planner-v1). Blocks are the only boundaries for domain switches."""

import asyncio
from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from app.api.deps import DB, Learner
from app.db.models import Session
from app.kernel import (
    adaptation,
    blocks,
    competency,
    memory,
    planner,
    practice,
    preferences,
    skill_graph,
)
from app.kernel import session as ksession

router = APIRouter(prefix="/plan", tags=["plan"])


ARM_PREF_KEYS = {"new_material_min": "planner.new_material_min", "review_min": "planner.review_min"}


async def build_plan(
    db: DB,
    learner_id: str,
    mode: str,
    energy: int,
    *,
    overrides: dict[str, Any] | None = None,
) -> planner.Plan:
    """`overrides` = an experiment arm's config for this session (e.g. new_material_min), merged
    over the learner's preferences; disclosed on the session screen."""
    nxt = await skill_graph.next_skill(db, learner_id)
    due = await memory.due_items(db, learner_id, cap=100, exclude_domains=("language",))
    prefs = await preferences.get_all(db, learner_id)
    for key, value in (overrides or {}).items():
        if key in ARM_PREF_KEYS:
            prefs[ARM_PREF_KEYS[key]] = value
    language_due = (
        await practice.language_due(db, learner_id) if prefs.get("planner.language") else 0
    )
    return planner.plan_session(
        planner.PlanInput(
            mode=mode,
            energy=energy,
            due_reviews=len(due),
            next_skill_id=nxt.id if nxt else None,
            next_skill_mastery=await competency.mastery(db, learner_id, nxt.id) if nxt else 0.0,
            review_node_ids=sorted({item.skill_id for item, _ in due}),
            language_due=language_due,
            guitar=bool(prefs.get("planner.guitar")),
            preferences=prefs,
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
    switched_early: bool | None = None
    reason: str | None = Field(
        default=None, pattern="^(finished|switch_early|skipped|save_and_stop|session_end)$"
    )
    grasp_passed: bool | None = None


class BlockAdvance(BaseModel):
    """End the block the client believes is current and start the next one (one server call)."""

    session_id: str
    from_index: int | None = Field(
        default=None, ge=0, description="idempotency key: the current block"
    )
    reason: str = Field(
        default="finished", pattern="^(finished|switch_early|skipped|save_and_stop)$"
    )
    grasp_passed: bool | None = None
    actual_min: float | None = None


class BlockExtend(BaseModel):
    session_id: str
    index: int = Field(ge=0)
    minutes: int = Field(default=5, ge=1, le=30)


BlockOut = blocks.BlockState


def session_lock(request: Request, session_id: str) -> asyncio.Lock:
    """One asyncio.Lock per session on `app.state` (no module singleton): transitions are
    read-check-write, so two concurrent requests must not both pass the check."""
    locks: dict[str, asyncio.Lock] | None = getattr(request.app.state, "transition_locks", None)
    if locks is None:
        locks = {}
        request.app.state.transition_locks = locks
    lock = locks.get(session_id)
    if lock is None:
        lock = locks[session_id] = asyncio.Lock()
        if len(locks) > 500:  # sessions are short-lived; drop idle locks
            for key in [k for k, v in list(locks.items()) if not v.locked()][:250]:
                locks.pop(key, None)
    return lock


@router.get(
    "/blocks/state",
    summary="Where the session is: block, phase, active skill",
    response_model=BlockOut,
)
async def block_state(session_id: str, db: DB) -> BlockOut:
    return await blocks.state(db, await ksession.get(db, session_id))


@router.post(
    "/blocks/start",
    summary="Start a planned block (emits block_started once; idempotent)",
    response_model=BlockOut,
)
async def start_block(body: BlockEvent, request: Request, db: DB) -> BlockOut:
    async with session_lock(request, body.session_id):
        return await blocks.start(db, await ksession.get(db, body.session_id), body.index)


@router.post(
    "/blocks/end",
    summary="End the running block (emits block_ended once; early switches out of new material need a grasp check)",
    response_model=BlockOut,
)
async def end_block(body: BlockEvent, request: Request, db: DB) -> BlockOut:
    async with session_lock(request, body.session_id):
        return await blocks.end(
            db,
            await ksession.get(db, body.session_id),
            body.index,
            reason=body.reason or "finished",
            switched_early=body.switched_early,
            grasp_passed=body.grasp_passed,
            actual_min=body.actual_min,
        )


@router.post(
    "/blocks/next",
    summary="End the current block and start the next one atomically (idempotent on from_index)",
    response_model=BlockOut,
)
async def next_block(body: BlockAdvance, request: Request, db: DB) -> BlockOut:
    async with session_lock(request, body.session_id):
        return await blocks.advance(
            db,
            await ksession.get(db, body.session_id),
            from_index=body.from_index,
            reason=body.reason,
            grasp_passed=body.grasp_passed,
            actual_min=body.actual_min,
        )


@router.post(
    "/blocks/extend",
    summary="Soft timer: give the running block N more minutes (kept across reloads)",
    response_model=BlockOut,
)
async def extend_block(body: BlockExtend, db: DB) -> BlockOut:
    return await blocks.extend(
        db, await ksession.get(db, body.session_id), body.index, body.minutes
    )


def _blocks(s: Session) -> list[planner.Block]:
    return blocks.blocks_of(s)


def plan_to_json(plan: planner.Plan) -> list[dict[str, Any]]:
    return [b.model_dump() for b in plan.blocks]


class ReplanIn(BaseModel):
    session_id: str
    energy: int = Field(ge=1, le=5)
    from_index: int = Field(ge=0, le=400, default=0, description="first block that may change")


class ReplanOut(BaseModel):
    proposal_id: str | None
    energy: int
    plan: planner.Plan
    changed: bool


@router.post(
    "/replan",
    summary="Energy check-in mid-session: records the new energy and proposes a re-scaled plan",
    response_model=ReplanOut,
)
async def replan(body: ReplanIn, db: DB, learner: Learner) -> ReplanOut:
    s = await ksession.get(db, body.session_id)
    if s.ended_at is not None:
        raise ValueError("session already ended")
    current = planner.Plan(
        mode=s.mode,
        energy=s.energy,
        blocks=_blocks(s),
        minimum_viable=["retrieval", "recap"],
        total_min=sum(b.planned_min for b in _blocks(s)),
    )
    new = planner.replan(current, from_index=body.from_index, energy=body.energy)
    s.energy = body.energy  # the learner said so: explicit, not an adaptation
    await db.commit()
    if [b.model_dump() for b in new.blocks] == [b.model_dump() for b in current.blocks]:
        return ReplanOut(proposal_id=None, energy=body.energy, plan=current, changed=False)
    remaining_old = sum(b.planned_min for b in current.blocks[body.from_index :])
    remaining_new = sum(b.planned_min for b in new.blocks[body.from_index :])
    card = await adaptation.propose(
        db,
        learner.id,
        what=f"Re-plan the rest of this session: {remaining_new} min instead of {remaining_old}",
        why=f"You set energy to {body.energy} (was {current.energy}).",
        pref="session.plan",
        value={"blocks": [b.model_dump() for b in new.blocks], "energy": body.energy},
        origin="planner",
        pattern=f"planner:replan:{s.id}",
        evidence={"energy_before": current.energy, "energy_after": body.energy},
        session=s,
    )
    return ReplanOut(proposal_id=card.id, energy=body.energy, plan=new, changed=True)
