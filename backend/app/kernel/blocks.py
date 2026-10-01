"""Server-authoritative block transitions (P1 `session-transitions`).

The session checkpoint is the single source of truth for *where the learner is*: which planned
block is running (`block_index`, `block_id`), since when (`block_started_at`), its `phase` (the
screen), the active `skill_id` (persisted — never a recomputed recommendation), the `plan_version`
(bumped when an accepted re-plan replaces blocks) and the soft-timer `timer_extension_min`.

Every transition is idempotent: starting a block that is already running, ending a block that is
not running, or advancing from an index that is no longer current returns the current state and
writes **no** event — so a retry or a double-click never duplicates `block_started`/`block_ended`.
`advance()` = end the running block + start the next one in one server call, so the client never
has to combine two requests with its own stale index. Callers serialise transitions per session
(`api.plan.session_lock`) so two concurrent requests cannot both pass the read-check; the event
and the checkpoint are committed together."""

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow_iso
from app.db.events import EventWriter, Verb
from app.db.models import LearningEvent, Session
from app.kernel import planner
from app.kernel import session as ksession
from app.schemas.common import ActivityType, Domain, ObjectType

Phase = Literal["practice", "review", "teach", "challenge", "recap"]
PHASE_FOR: dict[str, Phase] = {
    "movement_primer": "practice",
    "retrieval": "review",
    "new_material": "teach",
    "challenge": "challenge",
    "interleaved_review": "review",
    "domain_switch": "practice",
    "recap": "recap",
}
ACTIVITY_FOR: dict[str, ActivityType] = {
    "movement_primer": ActivityType.MOVEMENT,
    "retrieval": ActivityType.RETRIEVAL,
    "new_material": ActivityType.NEW_MATERIAL,
    "challenge": ActivityType.CHALLENGE,
    "interleaved_review": ActivityType.INTERLEAVED_REVIEW,
    "domain_switch": ActivityType.DOMAIN_SWITCH,
    "recap": ActivityType.RECAP,
}
END_REASONS = ("finished", "switch_early", "skipped", "save_and_stop", "session_end")
REVIEW_TYPES = ("retrieval", "interleaved_review")


class BlockState(BaseModel):
    """What the client renders from; returned by every transition and inside `SessionOut`."""

    block_index: int | None = None
    block: planner.Block | None = None
    block_id: str | None = None
    block_status: Literal["running", "ended"] | None = None
    block_started_at: str | None = None
    phase: str | None = None
    skill_id: str | None = None
    next_index: int | None = None
    plan_version: int = 1
    timer_extension_min: int = 0
    first_started_index: int | None = None  # blocks before it were passed over, not done
    plan_complete: bool = False
    allowed: bool = True
    message: str = ""


def phase_for(block_type: str) -> Phase:
    return PHASE_FOR.get(block_type, "teach")


def activity_for(block_type: str) -> ActivityType:
    return ACTIVITY_FOR.get(block_type, ActivityType.CHAT)


def domain_for(block: planner.Block) -> Domain:
    if block.domain in ("language", "guitar", "movement"):
        return Domain(block.domain)
    return Domain.AI_ML


def blocks_of(s: Session) -> list[planner.Block]:
    return [planner.Block.model_validate(b) for b in (s.planned_blocks_json or [])]


def next_index(blocks: list[planner.Block], index: int | None) -> int | None:
    if index is None:
        return 0 if blocks else None
    return index + 1 if index + 1 < len(blocks) else None


def _state_from(cp: dict[str, Any], blocks: list[planner.Block], **extra: Any) -> BlockState:
    idx = cp.get("block_index")
    idx = int(idx) if isinstance(idx, int) and 0 <= idx < len(blocks) else None
    status = cp.get("block_status")
    if (
        idx is not None
        and status == "running"
        and cp.get("block_type")
        and blocks[idx].type != cp.get("block_type")
    ):
        # the plan changed under the running block (should not happen since re-plans keep the
        # running block; defensive): treat it as ended so the learner can continue, never a dead end
        status = "ended"
        extra.setdefault(
            "message", "the plan changed under the running block; continue with the next"
        )
    return BlockState(
        block_index=idx,
        block=blocks[idx] if idx is not None else None,
        block_id=cp.get("block_id"),
        block_status=status if status in ("running", "ended") else None,
        block_started_at=cp.get("block_started_at"),
        phase=cp.get("phase"),
        skill_id=cp.get("skill_id"),
        next_index=next_index(blocks, idx) if idx is not None or blocks else None,
        plan_version=int(cp.get("plan_version") or 1),
        timer_extension_min=int(cp.get("timer_extension_min") or 0),
        first_started_index=(
            int(cp["first_started_index"])
            if isinstance(cp.get("first_started_index"), int)
            else None
        ),
        plan_complete=bool(
            idx is not None and status == "ended" and next_index(blocks, idx) is None
        ),
        **extra,
    )


async def state(db: AsyncSession, s: Session) -> BlockState:
    cp = await ksession.load_checkpoint(db, s.id) or {}
    return _state_from(cp, blocks_of(s))


async def _save(db: AsyncSession, s: Session, cp: dict[str, Any], update: dict[str, Any]) -> None:
    """Commit the checkpoint together with any event emitted with `commit=False` before it."""
    await ksession.save_checkpoint(db, s, {**cp, **update})


def _minutes_since(started: str | None) -> float | None:
    if not started:
        return None
    try:
        t0 = datetime.fromisoformat(started)
    except ValueError:
        return None
    if t0.tzinfo is None:
        t0 = t0.replace(tzinfo=UTC)
    return round(max(0.0, (datetime.now(UTC) - t0).total_seconds() / 60), 2)


async def _graded_since(db: AsyncSession, s: Session, cp: dict[str, Any]) -> bool:
    """Grasp evidence = any graded attempt on the active skill since this block started."""
    started = cp.get("block_started_at")
    skill_id = cp.get("skill_id")
    if not started or not skill_id:
        return False
    stmt = (
        select(LearningEvent.id)
        .where(
            LearningEvent.session_id == s.id,
            LearningEvent.verb == "attempted",
            LearningEvent.ts >= str(started),
        )
        .limit(50)
    )
    ids = list((await db.execute(stmt)).scalars())
    if not ids:
        return False
    rows = (await db.execute(select(LearningEvent).where(LearningEvent.id.in_(ids)))).scalars()
    return any((e.context_json or {}).get("node_id") == skill_id for e in rows)


async def start(db: AsyncSession, s: Session, index: int) -> BlockState:
    """Start block `index`. Idempotent when that block is already running. Refuses while another
    block is running (use `advance`), and after the session ended."""
    blocks = blocks_of(s)
    if not 0 <= index < len(blocks):
        raise KeyError("block index out of range")
    if s.ended_at is not None:
        raise ValueError("session already ended")
    cp = await ksession.load_checkpoint(db, s.id) or {}
    running = cp.get("block_status") == "running"
    if running and cp.get("block_index") == index:
        return _state_from(cp, blocks, message="already running")
    if running:
        return _state_from(
            cp, blocks, allowed=False, message=f"block {cp['block_index']} is still running"
        )
    b = blocks[index]
    events = EventWriter(
        db, ksession.event_context(s, domain=domain_for(b), activity=activity_for(b.type))
    )
    block_id = f"{s.id}:{index}"
    await events.emit(
        Verb.BLOCK_STARTED,
        ObjectType.BLOCK,
        block_id,
        context={"block_type": b.type, "planned_min": b.planned_min, "node_ids": b.node_ids},
        commit=False,  # committed together with the checkpoint below
    )
    skill_id = cp.get("skill_id")
    if b.type in ("new_material", "challenge") and b.node_ids:
        skill_id = b.node_ids[0]  # the block's node becomes the active skill
    update = {
        "block_index": index,
        "block_id": block_id,
        "block_type": b.type,
        "block_status": "running",
        "block_started_at": utcnow_iso(),
        "phase": phase_for(b.type),
        "skill_id": skill_id,
        "timer_extension_min": 0,
        "plan_version": int(cp.get("plan_version") or 1),
        "first_started_index": (
            cp["first_started_index"] if isinstance(cp.get("first_started_index"), int) else index
        ),
    }
    await _save(db, s, cp, update)
    return _state_from({**cp, **update}, blocks, message="started")


async def end(
    db: AsyncSession,
    s: Session,
    index: int,
    *,
    reason: str = "finished",
    switched_early: bool | None = None,
    grasp_passed: bool | None = None,
    actual_min: float | None = None,
) -> BlockState:
    """End the running block `index`. Idempotent: not running / already ended → current state,
    no event. An early switch out of new material needs the grasp check (planner rule)."""
    blocks = blocks_of(s)
    if not 0 <= index < len(blocks):
        raise KeyError("block index out of range")
    if reason not in END_REASONS:
        raise ValueError(f"reason must be one of {END_REASONS}")
    cp = await ksession.load_checkpoint(db, s.id) or {}
    if cp.get("block_index") != index or cp.get("block_status") != "running":
        return _state_from(cp, blocks, message="block not running; nothing to end")
    b = blocks[index]
    early = switched_early if switched_early is not None else reason != "finished"
    if b.grasp_check_required and reason not in ("save_and_stop", "session_end"):
        # new material ends with recall evidence — whatever the client calls the exit. The
        # client's flag is a hint; the evidence itself is in the event log (survives reloads).
        graded = bool(grasp_passed) or await _graded_since(db, s, cp)
        if not graded:
            return _state_from(
                cp,
                blocks,
                allowed=False,
                message="answer one recall item on this skill before leaving it (grasp check); "
                "Save & stop needs none",
            )
    elif early:
        ok, why = planner.can_switch_early(b, grasp_passed=True, reason=reason)
        if not ok:
            return _state_from(cp, blocks, allowed=False, message=why)
    events = EventWriter(
        db, ksession.event_context(s, domain=domain_for(b), activity=activity_for(b.type))
    )
    await events.emit(
        Verb.BLOCK_ENDED,
        ObjectType.BLOCK,
        str(cp.get("block_id") or f"{s.id}:{index}"),
        result={
            "actual_min": (
                actual_min if actual_min is not None else _minutes_since(cp.get("block_started_at"))
            ),
            "switched_early": early,
            "reason": reason,
            "timer_extension_min": int(cp.get("timer_extension_min") or 0),
        },
        context={"block_type": b.type, "planned_min": b.planned_min, "node_ids": b.node_ids},
        commit=False,
    )
    update = {"block_status": "ended"}
    await _save(db, s, cp, update)
    return _state_from({**cp, **update}, blocks, message="ended")


async def advance(
    db: AsyncSession,
    s: Session,
    *,
    from_index: int | None,
    reason: str = "finished",
    grasp_passed: bool | None = None,
    actual_min: float | None = None,
) -> BlockState:
    """End the block the client believes is current and start the next one — atomically on the
    server. `from_index` is the idempotency key: when it is no longer the current block (a retry
    after the first call succeeded) the current state is returned untouched."""
    blocks = blocks_of(s)
    cp = await ksession.load_checkpoint(db, s.id) or {}
    current = cp.get("block_index")
    if from_index is None:
        if current is not None and cp.get("block_status") == "running":
            return _state_from(cp, blocks, message="a block is already in progress")
        if current is not None:  # the last block ended (stop, then a change of mind): continue
            nxt0 = next_index(blocks, int(current))
            if nxt0 is None:
                return _state_from(cp, blocks, message="plan complete")
            return await start(db, s, nxt0)
        return await start(db, s, 0) if blocks else _state_from(cp, blocks, message="no plan")
    if current != from_index:
        return _state_from(cp, blocks, message="already advanced")
    if cp.get("block_status") == "running":
        ended = await end(
            db, s, from_index, reason=reason, grasp_passed=grasp_passed, actual_min=actual_min
        )
        if not ended.allowed:
            return ended
        if ended.block_status != "ended":
            return ended  # defensive: nothing changed
    nxt = next_index(blocks, from_index)
    if nxt is None:
        cp2 = await ksession.load_checkpoint(db, s.id) or {}
        return _state_from(cp2, blocks, message="plan complete")
    return await start(db, s, nxt)


async def extend(db: AsyncSession, s: Session, index: int, minutes: int) -> BlockState:
    """Soft-timer '+N minutes' for the running block; recorded so a reload keeps the deadline."""
    blocks = blocks_of(s)
    cp = await ksession.load_checkpoint(db, s.id) or {}
    if cp.get("block_index") != index or cp.get("block_status") != "running":
        return _state_from(cp, blocks, message="block not running")
    update = {"timer_extension_min": int(cp.get("timer_extension_min") or 0) + int(minutes)}
    await _save(db, s, cp, update)
    return _state_from({**cp, **update}, blocks, message="extended")


async def end_running(db: AsyncSession, s: Session, *, reason: str = "session_end") -> None:
    """Session end / stop: close the running block exactly once so no block stays half-open."""
    cp = await ksession.load_checkpoint(db, s.id) or {}
    if cp.get("block_status") == "running" and isinstance(cp.get("block_index"), int):
        await end(db, s, int(cp["block_index"]), reason=reason, switched_early=True)


async def bump_plan_version(db: AsyncSession, s: Session) -> int:
    """Called when an accepted (or undone) re-plan replaced `planned_blocks_json`: clients
    compare `plan_version` to refetch; the running block keeps its start time."""
    cp = await ksession.load_checkpoint(db, s.id) or {}
    v = int(cp.get("plan_version") or 1) + 1
    await _save(db, s, cp, {"plan_version": v})
    return v
