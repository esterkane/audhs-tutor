"""Adaptation proposals (ADR-0003/0006, AuDHD invariant "no covert adaptation").

The kernel *observes* patterns in the event log and *proposes* a change as a card:
Try (this session only) / Make default / No (ask again in 14 days) / Don't suggest again.
Every accepted change is applied through the preference registry with origin
`proposed_accepted`, logged as `adapted`, and reversible with one action (`undone`).
Trials expire when the next session starts. Nothing here calls a model."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.events import EventContext, EventWriter, Verb
from app.db.models import Adaptation, AdaptationDecision, LearningEvent, Session
from app.kernel import competency, memory, preferences
from app.kernel.skill_graph import MASTERY_DONE
from app.schemas.common import Mode, ObjectType

POLICY_VERSION = "adapt.v1"
DECISIONS = ("try", "default", "no", "never")
RE_ASK_AFTER_DAYS = 14


@dataclass
class Proposal:
    pattern: str
    what: str  # literal, learner-facing
    why: str  # the observed numbers in words
    pref: str
    value: Any
    evidence: dict[str, Any]


Detector = Callable[[AsyncSession, str, dict[str, Any]], Awaitable[Proposal | None]]


async def _recent_events(
    db: AsyncSession, learner_id: str, verb: Verb, *, limit: int
) -> list[LearningEvent]:
    stmt = (
        select(LearningEvent)
        .where(LearningEvent.learner_id == learner_id, LearningEvent.verb == str(verb))
        .order_by(LearningEvent.ts.desc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


async def _recent_sessions(db: AsyncSession, learner_id: str, *, limit: int) -> list[Session]:
    stmt = (
        select(Session)
        .where(Session.learner_id == learner_id, Session.ended_at.is_not(None))
        .order_by(Session.started_at.desc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


# ----------------------------------------------------------------------------- rules
async def hint_heavy(db: AsyncSession, learner_id: str, prefs: dict[str, Any]) -> Proposal | None:
    """Many hints per attempt → start with a worked example instead of a bare problem."""
    if prefs.get("tutor.representation_default") == "worked_example":
        return None
    attempts = await _recent_events(db, learner_id, Verb.ATTEMPTED, limit=12)
    # only attempts on skills not yet mastered count: worked examples first is for new material
    mastery_cache: dict[str, float] = {}
    scoped = []
    for e in attempts:
        node_id = str((e.context_json or {}).get("node_id") or "")
        if node_id and node_id not in mastery_cache:
            mastery_cache[node_id] = await competency.mastery(db, learner_id, node_id)
        if mastery_cache.get(node_id, 0.0) < MASTERY_DONE:
            scoped.append(e)
    if len(scoped) < 6:
        return None
    hints = [int((e.result_json or {}).get("hint_count") or 0) for e in scoped]
    avg = sum(hints) / len(hints)
    if avg < 2.5:
        return None
    return Proposal(
        pattern="hint_heavy",
        what="Start new material with a worked example (for skills you have not yet mastered)",
        why=f"You used {avg:.1f} hints per attempt over the last {len(hints)} attempts on unmastered skills.",
        pref="tutor.representation_default",
        value="worked_example",
        evidence={"attempts": len(hints), "avg_hint_count": round(avg, 2)},
    )


async def early_exit(db: AsyncSession, learner_id: str, prefs: dict[str, Any]) -> Proposal | None:
    """New-material blocks left early → plan shorter new-material blocks."""
    current = int(prefs.get("planner.new_material_min", 20))
    if current <= 5:
        return None
    ends = await _recent_events(db, learner_id, Verb.BLOCK_ENDED, limit=25)
    new_blocks = [e for e in ends if (e.context_json or {}).get("block_type") == "new_material"]
    recent = new_blocks[:5]
    early = [
        e
        for e in recent
        if (e.result_json or {}).get("switched_early")
        and (e.result_json or {}).get("reason") not in ("save_and_stop", "skipped")
    ]  # honouring the soft timer is not an early exit
    if len(recent) < 3 or len(early) < 2:
        return None
    return Proposal(
        pattern="early_exit",
        what=f"Plan {max(5, current - 5)} minutes of new material instead of {current}",
        why=f"{len(early)} of your last {len(recent)} new-material blocks ended early.",
        pref="planner.new_material_min",
        value=max(5, current - 5),
        evidence={"blocks": len(recent), "early": len(early), "current_min": current},
    )


async def movement_skipped(
    db: AsyncSession, learner_id: str, prefs: dict[str, Any]
) -> Proposal | None:
    """Movement primers skipped repeatedly → stop planning them."""
    if prefs.get("planner.movement") == "off":
        return None
    ends = await _recent_events(db, learner_id, Verb.BLOCK_ENDED, limit=40)
    movement = [e for e in ends if (e.context_json or {}).get("block_type") == "movement_primer"]
    recent = movement[:5]
    skipped = [e for e in recent if (e.result_json or {}).get("reason") == "skipped"]
    if len(recent) < 3 or len(skipped) < 3:
        return None
    return Proposal(
        pattern="movement_skipped",
        what="Leave movement out of the plan",
        why=f"You skipped {len(skipped)} of the last {len(recent)} movement blocks.",
        pref="planner.movement",
        value="off",
        evidence={"blocks": len(recent), "skipped": len(skipped)},
    )


async def review_backlog(
    db: AsyncSession, learner_id: str, prefs: dict[str, Any]
) -> Proposal | None:
    """A standing review backlog → a longer review block."""
    current = int(prefs.get("planner.review_min", 10))
    spec = preferences.PREFERENCES["planner.review_min"]
    if spec.max is not None and current >= spec.max:
        return None
    # AI/ML cards only: vocabulary belongs to the language block, not the review block
    due = len(await memory.due_items(db, learner_id, cap=500, exclude_domains=("language",)))
    if int(due) < 15:
        return None
    value = min(current + 5, spec.max or current + 5)
    return Proposal(
        pattern="review_backlog",
        what=f"Plan {value} minutes of review instead of {current}",
        why=f"{due} items are due right now; the review block has not been keeping up.",
        pref="planner.review_min",
        value=value,
        evidence={"due": int(due), "current_min": current},
    )


async def low_energy_sessions(
    db: AsyncSession, learner_id: str, prefs: dict[str, Any]
) -> Proposal | None:
    """Most recent sessions started at low energy → preselect Low capacity on Home."""
    if prefs.get("session.default_mode") == "low_capacity":
        return None
    sessions = await _recent_sessions(db, learner_id, limit=5)
    low = [s for s in sessions if s.energy <= 2]
    if len(sessions) < 4 or len(low) < 3:
        return None
    return Proposal(
        pattern="low_energy_sessions",
        what="Preselect Low capacity on Home",
        why=f"{len(low)} of your last {len(sessions)} sessions ran at energy 2 or lower.",
        pref="session.default_mode",
        value="low_capacity",
        evidence={"sessions": len(sessions), "low_energy": len(low)},
    )


RULES: list[Detector] = [
    hint_heavy,
    early_exit,
    movement_skipped,
    review_backlog,
    low_energy_sessions,
]


# ----------------------------------------------------------------------------- engine
def _ctx(learner_id: str, session: Session | None) -> EventContext:
    if session is None:
        return EventContext(learner_id=learner_id, session_id=None, mode=Mode.STEADY, energy=3)
    return EventContext(
        learner_id=learner_id,
        session_id=session.id,
        mode=Mode(session.mode),
        energy=session.energy,
        socratic=session.socratic,
    )


async def _latest_decision(db: AsyncSession, adaptation_id: str) -> AdaptationDecision | None:
    stmt = (
        select(AdaptationDecision)
        .where(AdaptationDecision.adaptation_id == adaptation_id)
        .order_by(AdaptationDecision.decided_at.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def _blocked(db: AsyncSession, learner_id: str, pattern: str) -> bool:
    """A pattern is not re-proposed while a card is open, after 'never', within 14 days of 'no',
    or while a 'default' decision for it is in effect."""
    rows = list(
        (
            await db.execute(
                select(Adaptation).where(
                    Adaptation.learner_id == learner_id, Adaptation.pattern == pattern
                )
            )
        ).scalars()
    )
    cutoff = (datetime.now(UTC) - timedelta(days=RE_ASK_AFTER_DAYS)).isoformat(timespec="seconds")
    for a in rows:
        d = await _latest_decision(db, a.id)
        if d is None or d.decision == "never":
            return True
        if d.decision == "no" and d.decided_at >= cutoff:
            return True
        if d.decision in ("try", "default") and d.undone_at is None:
            return True  # in effect (a trial or a default): never stack a second card on top
    return False


async def observe(
    db: AsyncSession, learner_id: str, *, session: Session | None = None
) -> list[Adaptation]:
    """Run every rule; create a card for each new pattern; return all open cards."""
    prefs = await preferences.get_all(db, learner_id)
    events = EventWriter(db, _ctx(learner_id, session))
    for rule in RULES:
        proposal = await rule(db, learner_id, prefs)
        if proposal is None or await _blocked(db, learner_id, proposal.pattern):
            continue
        row = Adaptation(
            learner_id=learner_id,
            what=proposal.what,
            why=proposal.why,
            origin="observed_pattern",
            policy_version=POLICY_VERSION,
            reversible=True,
            pattern=proposal.pattern,
            apply_json={"pref": proposal.pref, "value": proposal.value},
            evidence_json=proposal.evidence,
        )
        db.add(row)
        await db.commit()
        await events.emit(
            Verb.PROPOSED,
            ObjectType.ADAPTATION,
            row.id,
            result={"decision": None},
            context={"what": proposal.what, "why": proposal.why, "origin": "observed_pattern"},
        )
    return await pending(db, learner_id)


async def propose(
    db: AsyncSession,
    learner_id: str,
    *,
    what: str,
    why: str,
    pref: str,
    value: Any,
    origin: str = "planner",
    pattern: str = "",
    evidence: dict[str, Any] | None = None,
    session: Session | None = None,
) -> Adaptation:
    """A card raised by the planner (or any kernel component) rather than by a rule.
    `pref` may be a preference key, or the literal "session.plan" with `value` = a plan (dict):
    then deciding replaces the session's remaining blocks instead of a preference."""
    if pref == "session.plan":
        if session is None or not isinstance(value, dict):
            raise ValueError("a plan proposal needs a session and a plan")
    else:
        preferences.validate(pref, value)
    pattern = pattern or f"{origin}:{pref}"
    if await _blocked(db, learner_id, pattern):
        # one card per pattern: open, in effect (trial/default), 'never', or a recent 'no'
        stmt = (
            select(Adaptation)
            .where(Adaptation.learner_id == learner_id, Adaptation.pattern == pattern)
            .order_by(Adaptation.proposed_at.desc())
            .limit(1)
        )
        existing = (await db.execute(stmt)).scalar_one()
        return existing
    row = Adaptation(
        learner_id=learner_id,
        what=what,
        why=why,
        origin=origin,
        policy_version=POLICY_VERSION,
        pattern=pattern,
        apply_json={"pref": pref, "value": value},
        evidence_json=evidence or {},
        session_id=session.id if session else None,
    )
    db.add(row)
    await db.commit()
    await EventWriter(db, _ctx(learner_id, session)).emit(
        Verb.PROPOSED,
        ObjectType.ADAPTATION,
        row.id,
        result={"decision": None},
        context={"what": what, "why": why, "origin": origin},
    )
    return row


async def pending(db: AsyncSession, learner_id: str) -> list[Adaptation]:
    rows = list(
        (
            await db.execute(
                select(Adaptation)
                .where(Adaptation.learner_id == learner_id)
                .order_by(Adaptation.proposed_at.desc())
            )
        ).scalars()
    )
    return [a for a in rows if await _latest_decision(db, a.id) is None]


@dataclass
class HistoryEntry:
    adaptation: Adaptation
    decision: str | None
    decided_at: str | None
    undone_at: str | None
    in_effect: bool


async def history(db: AsyncSession, learner_id: str, *, limit: int = 50) -> list[HistoryEntry]:
    rows = list(
        (
            await db.execute(
                select(Adaptation)
                .where(Adaptation.learner_id == learner_id)
                .order_by(Adaptation.proposed_at.desc())
                .limit(limit)
            )
        ).scalars()
    )
    out = []
    for a in rows:
        d = await _latest_decision(db, a.id)
        out.append(
            HistoryEntry(
                adaptation=a,
                decision=d.decision if d else None,
                decided_at=d.decided_at if d else None,
                undone_at=d.undone_at if d else None,
                in_effect=bool(d and d.decision in ("try", "default") and d.undone_at is None),
            )
        )
    return out


async def decide(
    db: AsyncSession,
    learner_id: str,
    adaptation_id: str,
    decision: str,
    *,
    session: Session | None = None,
) -> AdaptationDecision:
    if decision not in DECISIONS:
        raise ValueError(f"decision must be one of {DECISIONS}")
    a = await db.get(Adaptation, adaptation_id)
    if a is None or a.learner_id != learner_id:
        raise KeyError(adaptation_id)
    if await _latest_decision(db, a.id) is not None:
        raise ValueError("this proposal was already decided")
    if decision == "try" and session is None:
        raise ValueError("'Try it this session' needs a running session")
    if decision == "default" and a.apply_json.get("pref") == "session.plan":
        raise ValueError("a plan applies to one session; there is no default to set")
    events = EventWriter(db, _ctx(learner_id, session))
    if decision in ("try", "default"):
        pref, value = a.apply_json["pref"], a.apply_json["value"]
        if pref == "session.plan":
            target = await db.get(Session, a.session_id) if a.session_id else session
            if target is None:
                raise ValueError("the session of this plan proposal no longer exists")
            a.previous_json = {"value": list(target.planned_blocks_json or [])}
            target.planned_blocks_json = list(value["blocks"])
            await db.commit()
            await events.emit(
                Verb.ADAPTED,
                ObjectType.ADAPTATION,
                a.id,
                context={
                    "what": a.what,
                    "why": a.why,
                    "reversible": True,
                    "policy_version": POLICY_VERSION,
                },
            )
        else:
            a.previous_json = {
                "value": await preferences.get(db, learner_id, pref),
                "was_set": await preferences.is_set(db, learner_id, pref),
            }
            a.session_id = session.id if (decision == "try" and session) else None
            await preferences.set_pref(
                db,
                learner_id,
                pref,
                value,
                origin="proposed_accepted",
                events=events,
                event_object_id=a.id,
                policy_version=POLICY_VERSION,
            )
    row = AdaptationDecision(learner_id=learner_id, adaptation_id=a.id, decision=decision)
    db.add(row)
    await db.commit()
    await events.emit(
        Verb.DECIDED,
        ObjectType.ADAPTATION,
        a.id,
        result={"decision": decision},
        context={"what": a.what, "why": a.why, "origin": a.origin},
    )
    return row


async def undo(
    db: AsyncSession,
    learner_id: str,
    adaptation_id: str,
    *,
    session: Session | None = None,
    why: str = "undone by the learner",
) -> AdaptationDecision:
    a = await db.get(Adaptation, adaptation_id)
    if a is None or a.learner_id != learner_id:
        raise KeyError(adaptation_id)
    d = await _latest_decision(db, a.id)
    if d is None or d.decision not in ("try", "default") or d.undone_at is not None:
        raise ValueError("nothing to undo")
    prev = a.previous_json or {}
    previous = prev.get("value")
    pref = a.apply_json["pref"]
    if pref == "session.plan":
        target = await db.get(Session, a.session_id) if a.session_id else None
        if target is not None and isinstance(previous, list):
            target.planned_blocks_json = previous
    elif previous is None or prev.get("was_set") is False:
        await preferences.reset(db, learner_id, pref)  # it was the default before: back to default
    else:
        await preferences.set_pref(db, learner_id, pref, previous, origin="explicit")
    d.undone_at = datetime.now(UTC).isoformat(timespec="seconds")
    await db.commit()
    await EventWriter(db, _ctx(learner_id, session)).emit(
        Verb.UNDONE,
        ObjectType.ADAPTATION,
        a.id,
        context={"what": a.what, "why": why, "reversible": True, "policy_version": POLICY_VERSION},
    )
    return d


async def expire_trials(db: AsyncSession, learner_id: str, *, current_session: Session) -> int:
    """'Try' means one session: when a new session starts, earlier trials are reverted (logged)."""
    rows = list(
        (
            await db.execute(
                select(Adaptation).where(
                    Adaptation.learner_id == learner_id,
                    Adaptation.session_id.is_not(None),
                    Adaptation.session_id != current_session.id,
                )
            )
        ).scalars()
    )
    n = 0
    for a in rows:
        if a.apply_json.get("pref") == "session.plan":
            continue  # a plan lives and dies with its session
        d = await _latest_decision(db, a.id)
        if d and d.decision == "try" and d.undone_at is None:
            await undo(db, learner_id, a.id, session=current_session, why="trial session ended")
            n += 1
    return n
