"""n-of-1 experiments (ADR-0005 step 3 groundwork; ARCHITECTURE §8 evaluation).

An experiment compares 2+ arms (e.g. Socratic vs explicit) on matched units — skill nodes by
default (each node is taught under one arm for its whole life), or sessions. Assignment is
balanced and deterministic, disclosed to the learner (the session banner) and logged (`assigned`).
Outcomes are read from the event log, never from a hidden score: delayed recall, error rate,
latency, completion, voluntary continuation, transfer. Results are shown as hypotheses with the
raw numbers and a plain confidence interval; nothing here calls a model."""

import hashlib
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow_iso
from app.db.events import EventContext, EventWriter, Verb
from app.db.models import (
    Experiment,
    ExperimentArm,
    ExperimentAssignment,
    ExperimentObservation,
    LearningEvent,
    Session,
)
from app.schemas.common import Mode, ObjectType

METRICS = (
    "delayed_recall",  # reviewed ≥ 1 day later: rating ≥ 3 (Good/Easy) share, higher is better
    "error_rate",  # attempted: correct == False share, 0–1, lower is better
    "latency_ms",  # attempted: mean latency, lower is better
    "completion",  # block_ended: not switched early share, 0–1, higher is better
    "voluntary_continuation",  # sessions that ran longer than planned, 0–1
    "transfer",  # evidenced: mean score on the transfer dimension, 0–1
)
LOWER_IS_BETTER = {"error_rate", "latency_ms"}
DIRECTIONLESS = {"voluntary_continuation"}  # engagement proxy: reported, never optimised
UNIT_TYPES = ("node", "session")
ARM_CONFIG_KEYS = {"socratic", "representation", "new_material_min"}

TEMPLATES: dict[str, dict[str, Any]] = {
    "socratic-vs-explicit": {
        "name": "Socratic vs explicit",
        "hypothesis": "Socratic questioning improves delayed recall on matched nodes without raising error rate.",
        "metric": "delayed_recall",
        "unit_type": "node",
        "arms": [
            {"name": "explicit", "config": {"socratic": False}},
            {"name": "socratic", "config": {"socratic": True}},
        ],
    },
    "worked-example-vs-problem-first": {
        "name": "Worked example first vs problem first",
        "hypothesis": "Starting with a worked example lowers hint use and keeps delayed recall.",
        "metric": "delayed_recall",
        "unit_type": "node",
        "arms": [
            {"name": "worked_example", "config": {"representation": "worked_example"}},
            {"name": "problem_first", "config": {"representation": "problem_first"}},
        ],
    },
    "short-vs-long-blocks": {
        "name": "Short vs long new-material blocks",
        "hypothesis": "Shorter blocks raise completion without hurting delayed recall.",
        "metric": "completion",
        "unit_type": "session",
        "arms": [
            {"name": "short", "config": {"new_material_min": 10}},
            {"name": "long", "config": {"new_material_min": 25}},
        ],
    },
}


@dataclass
class ArmStats:
    arm_id: str
    name: str
    n: int
    mean: float | None
    sd: float | None


@dataclass
class MetricResult:
    metric: str
    arms: list[ArmStats]
    difference: float | None  # arm[1] − arm[0]
    ci95: tuple[float, float] | None
    reading: str  # literal hypothesis wording
    lower_is_better: bool


@dataclass
class Results:
    experiment: Experiment
    arms: list[ExperimentArm]
    assignments: dict[str, int]
    metrics: list[MetricResult] = field(default_factory=list)


# ----------------------------------------------------------------------------- lifecycle
def _ctx(learner_id: str) -> EventContext:
    return EventContext(learner_id=learner_id, session_id=None, mode=Mode.STEADY, energy=3)


async def create(
    db: AsyncSession,
    learner_id: str,
    *,
    name: str,
    hypothesis: str,
    metric: str,
    arms: list[dict[str, Any]],
    unit_type: str = "node",
) -> Experiment:
    if metric not in METRICS:
        raise ValueError(f"metric must be one of {METRICS}")
    if unit_type not in UNIT_TYPES:
        raise ValueError(f"unit_type must be one of {UNIT_TYPES}")
    if len(arms) < 2:
        raise ValueError("an experiment needs at least two arms")
    for a in arms:
        unknown = set(a.get("config", {})) - ARM_CONFIG_KEYS
        if unknown:
            raise ValueError(
                f"unknown arm config keys {sorted(unknown)}; allowed {sorted(ARM_CONFIG_KEYS)}"
            )
    exp = Experiment(
        learner_id=learner_id, name=name, hypothesis=hypothesis, metric=metric, unit_type=unit_type
    )
    db.add(exp)
    await db.flush()
    for a in arms:
        db.add(
            ExperimentArm(
                experiment_id=exp.id, name=str(a["name"]), config_json=dict(a.get("config", {}))
            )
        )
    await db.commit()
    return exp


async def from_template(db: AsyncSession, learner_id: str, template: str) -> Experiment:
    t = TEMPLATES.get(template)
    if t is None:
        raise KeyError(template)
    return await create(
        db,
        learner_id,
        name=t["name"],
        hypothesis=t["hypothesis"],
        metric=t["metric"],
        arms=t["arms"],
        unit_type=t["unit_type"],
    )


async def get(db: AsyncSession, learner_id: str, experiment_id: str) -> Experiment:
    exp = await db.get(Experiment, experiment_id)
    if exp is None or exp.learner_id != learner_id:
        raise KeyError(experiment_id)
    return exp


async def arms_of(db: AsyncSession, experiment_id: str) -> list[ExperimentArm]:
    stmt = select(ExperimentArm).where(ExperimentArm.experiment_id == experiment_id)
    return list((await db.execute(stmt)).scalars().all())


async def list_all(db: AsyncSession, learner_id: str) -> list[Experiment]:
    stmt = (
        select(Experiment)
        .where(Experiment.learner_id == learner_id)
        .order_by(Experiment.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def running(db: AsyncSession, learner_id: str, *, unit_type: str) -> list[Experiment]:
    stmt = select(Experiment).where(
        Experiment.learner_id == learner_id,
        Experiment.status == "running",
        Experiment.unit_type == unit_type,
    )
    return list((await db.execute(stmt)).scalars().all())


async def start(db: AsyncSession, learner_id: str, experiment_id: str) -> Experiment:
    exp = await get(db, learner_id, experiment_id)
    if exp.status == "done":
        raise ValueError("a finished experiment cannot be restarted; create a new one")
    others = await running(db, learner_id, unit_type=exp.unit_type)
    if any(o.id != exp.id for o in others):
        raise ValueError(f"another {exp.unit_type}-unit experiment is already running")
    exp.status, exp.started_at = "running", utcnow_iso()
    await db.commit()
    return exp


async def stop(db: AsyncSession, learner_id: str, experiment_id: str) -> Experiment:
    exp = await get(db, learner_id, experiment_id)
    exp.status, exp.ended_at = "done", utcnow_iso()
    await db.commit()
    return exp


# ----------------------------------------------------------------------------- assignment
async def assignment_for(
    db: AsyncSession, experiment_id: str, unit_id: str
) -> ExperimentAssignment | None:
    stmt = select(ExperimentAssignment).where(
        ExperimentAssignment.experiment_id == experiment_id,
        ExperimentAssignment.unit_id == unit_id,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def assign(
    db: AsyncSession,
    learner_id: str,
    experiment: Experiment,
    *,
    unit_id: str,
    session: Session | None = None,
) -> ExperimentArm:
    """Balanced: the arm with the fewest units so far; ties broken by a hash of the unit id so the
    choice is reproducible. Idempotent per unit."""
    existing = await assignment_for(db, experiment.id, unit_id)
    arms = await arms_of(db, experiment.id)
    by_id = {a.id: a for a in arms}
    if existing is not None:
        return by_id[existing.arm_id]
    counts = {a.id: 0 for a in arms}
    stmt = select(ExperimentAssignment.arm_id).where(
        ExperimentAssignment.experiment_id == experiment.id
    )
    for arm_id in (await db.execute(stmt)).scalars():
        counts[arm_id] = counts.get(arm_id, 0) + 1
    least = min(counts.values())
    candidates = [a for a in arms if counts[a.id] == least]
    pick = candidates[int(hashlib.sha256(unit_id.encode()).hexdigest(), 16) % len(candidates)]
    db.add(
        ExperimentAssignment(
            learner_id=learner_id,
            experiment_id=experiment.id,
            arm_id=pick.id,
            unit_type=experiment.unit_type,
            unit_id=unit_id,
        )
    )
    try:
        await db.commit()
    except IntegrityError:  # a concurrent first contact won the unique (experiment, unit) race
        await db.rollback()
        winner = await assignment_for(db, experiment.id, unit_id)
        assert winner is not None
        return by_id[winner.arm_id]
    ctx = _ctx(learner_id)
    if session is not None:
        ctx = EventContext(
            learner_id=learner_id,
            session_id=session.id,
            mode=Mode(session.mode),
            energy=session.energy,
            socratic=session.socratic,
            experiment_arm=pick.id,
        )
    await EventWriter(db, ctx).emit(
        Verb.ASSIGNED,
        ObjectType.EXPERIMENT,
        experiment.id,
        result={
            "arm": pick.name,
            "metric": experiment.metric,
            "value": 0.0,
            "n": counts[pick.id] + 1,
        },
        context={"experiment_id": experiment.id},
    )
    return pick


async def arm_for_node(
    db: AsyncSession, learner_id: str, node_id: str, *, session: Session | None = None
) -> tuple[Experiment, ExperimentArm] | None:
    """The running node-unit experiment's arm for this node (assigning it on first contact)."""
    exps = await running(db, learner_id, unit_type="node")
    if not exps:
        return None
    exp = exps[0]
    return exp, await assign(db, learner_id, exp, unit_id=node_id, session=session)


async def arm_for_session(
    db: AsyncSession, learner_id: str, session: Session
) -> tuple[Experiment, ExperimentArm] | None:
    exps = await running(db, learner_id, unit_type="session")
    if not exps:
        return None
    exp = exps[0]
    arm = await assign(db, learner_id, exp, unit_id=session.id, session=session)
    session.experiment_arm_id = arm.id
    if "socratic" in arm.config_json:
        session.socratic = bool(arm.config_json["socratic"])
    await db.commit()
    return exp, arm


# ----------------------------------------------------------------------------- outcomes
_T95 = {
    1: 12.706,
    2: 4.303,
    3: 3.182,
    4: 2.776,
    5: 2.571,
    6: 2.447,
    7: 2.365,
    8: 2.306,
    9: 2.262,
    10: 2.228,
    12: 2.179,
    14: 2.145,
    16: 2.120,
    18: 2.101,
    20: 2.086,
    25: 2.060,
    30: 2.042,
}


def _t95(df: int) -> float:
    """Two-sided 95 % t critical value (small-sample honest; → 1.96 for large df)."""
    if df <= 0:
        return 12.706
    for k in sorted(_T95):
        if df <= k:
            return _T95[k]
    return 1.96


def _mean_sd(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    mean = sum(values) / len(values)
    if len(values) < 2:
        return mean, None
    var = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return mean, math.sqrt(var)


async def _unit_of_event(exp: Experiment, e: LearningEvent) -> str | None:
    if exp.unit_type == "session":
        return e.session_id
    ctx = e.context_json or {}
    node = ctx.get("node_id")
    return str(node) if node else None


async def outcomes(
    db: AsyncSession, learner_id: str, exp: Experiment
) -> dict[str, dict[str, list[float]]]:
    """metric → arm_id → per-event values, joined through the unit's assignment."""
    stmt = select(ExperimentAssignment).where(ExperimentAssignment.experiment_id == exp.id)
    arm_of_unit = {a.unit_id: a.arm_id for a in (await db.execute(stmt)).scalars()}
    ev_stmt = (
        select(LearningEvent)
        .where(
            LearningEvent.learner_id == learner_id,
            LearningEvent.verb.in_(("reviewed", "attempted", "block_ended", "evidenced")),
        )
        .order_by(LearningEvent.ts)
    )
    if exp.started_at:
        ev_stmt = ev_stmt.where(LearningEvent.ts >= exp.started_at)
    events = list((await db.execute(ev_stmt)).scalars())
    if exp.ended_at:
        # the window bounds *learning* (assignment stops at Stop); delayed reviews and evidence
        # for already-assigned units keep counting afterwards — that is the outcome
        events = [e for e in events if e.verb in ("reviewed", "evidenced") or e.ts <= exp.ended_at]
    out: dict[str, dict[str, list[float]]] = {m: {} for m in METRICS}

    def add(metric: str, arm_id: str, value: float) -> None:
        out[metric].setdefault(arm_id, []).append(value)

    for e in events:
        unit = await _unit_of_event(exp, e)
        arm_id = arm_of_unit.get(unit or "")
        if arm_id is None:
            continue
        r = e.result_json or {}
        if e.verb == "reviewed" and r.get("rating") is not None:
            # only *delayed* reviews count: the grader's same-session FSRS update is not recall
            if float(r.get("days_since_learned") or 0.0) >= 1.0:
                add("delayed_recall", arm_id, 1.0 if int(r["rating"]) >= 3 else 0.0)
        elif e.verb == "attempted":
            if r.get("correct") is not None:
                add("error_rate", arm_id, 0.0 if r["correct"] else 1.0)
            if r.get("latency_ms") is not None:
                add("latency_ms", arm_id, float(r["latency_ms"]))
        elif e.verb == "block_ended":
            add("completion", arm_id, 0.0 if r.get("switched_early") else 1.0)
        elif e.verb == "evidenced" and r.get("dimension") == "transfer":
            add("transfer", arm_id, float(r.get("score") or 0.0))
    if exp.unit_type == "session":
        sessions = list(
            (
                await db.execute(
                    select(Session).where(
                        Session.learner_id == learner_id, Session.ended_at.is_not(None)
                    )
                )
            ).scalars()
        )
        for s in sessions:
            arm_id = arm_of_unit.get(s.id)
            if arm_id is None or not s.ended_at:
                continue
            planned = sum(int(b.get("planned_min", 0)) for b in (s.planned_blocks_json or []))
            if planned <= 0:
                continue  # no plan, nothing to run past
            actual = (
                datetime.fromisoformat(s.ended_at) - datetime.fromisoformat(s.started_at)
            ).total_seconds() / 60
            add("voluntary_continuation", arm_id, 1.0 if actual > planned else 0.0)
    return out


MIN_N_FOR_SUPPORT = 10  # below this the normal approximation is a reading aid, not evidence


def _reading(
    metric: str,
    a: ArmStats,
    b: ArmStats,
    diff: float | None,
    ci: tuple[float, float] | None,
    *,
    primary: bool = False,
) -> str:
    if a.mean is None or b.mean is None or diff is None:
        return "Not enough data yet for this metric."
    ci_txt = f"; 95% CI {ci[0]:+.3f} to {ci[1]:+.3f}" if ci else ""
    n_txt = f"n={a.n}+{b.n}"
    if metric in DIRECTIONLESS:
        return (
            f"{metric.replace('_', ' ')}: {a.name} {a.mean:.2f} vs {b.name} {b.mean:.2f} "
            f"(difference {diff:+.3f}{ci_txt}; {n_txt}). Neither direction is 'better' here."
        )
    clear = ci is not None and (ci[0] > 0 or ci[1] < 0)
    if not clear:
        return (
            f"No clear difference yet on {metric.replace('_', ' ')} (difference {diff:+.3f}"
            f"{ci_txt}; {n_txt}). Keep going or stop: your call."
        )
    winner = b.name if (diff < 0) == (metric in LOWER_IS_BETTER) else a.name
    small = min(a.n, b.n) < MIN_N_FOR_SUPPORT
    if primary and not small:
        return (
            f"Hypothesis supported so far: {winner} is ahead on {metric.replace('_', ' ')} "
            f"(difference {diff:+.3f}{ci_txt}; {n_txt})."
        )
    return (
        f"Difference favours {winner} on {metric.replace('_', ' ')} (difference {diff:+.3f}"
        f"{ci_txt}; {n_txt}). Normal approximation at small n: a reading aid, not proof."
    )


async def results(
    db: AsyncSession, learner_id: str, experiment_id: str, *, record: bool = False
) -> Results:
    exp = await get(db, learner_id, experiment_id)
    arms = await arms_of(db, exp.id)
    data = await outcomes(db, learner_id, exp)
    stmt = select(ExperimentAssignment.arm_id).where(ExperimentAssignment.experiment_id == exp.id)
    counts: dict[str, int] = {a.id: 0 for a in arms}
    for arm_id in (await db.execute(stmt)).scalars():
        counts[arm_id] = counts.get(arm_id, 0) + 1
    res = Results(experiment=exp, arms=arms, assignments={a.name: counts[a.id] for a in arms})
    events = EventWriter(db, _ctx(learner_id)) if record else None
    for metric in METRICS:
        stats = []
        for a in arms:
            vals = data[metric].get(a.id, [])
            mean, sd = _mean_sd(vals)
            stats.append(ArmStats(arm_id=a.id, name=a.name, n=len(vals), mean=mean, sd=sd))
            if events is not None and mean is not None:
                db.add(
                    ExperimentObservation(
                        learner_id=learner_id,
                        experiment_id=exp.id,
                        arm_id=a.id,
                        metric=metric,
                        value=mean,
                        n=len(vals),
                    )
                )
                await events.emit(
                    Verb.MEASURED,
                    ObjectType.EXPERIMENT,
                    exp.id,
                    result={
                        "arm": a.name,
                        "metric": metric,
                        "value": round(mean, 4),
                        "n": len(vals),
                    },
                    context={"experiment_id": exp.id},
                )
        diff: float | None = None
        ci: tuple[float, float] | None = None
        if len(stats) >= 2:
            s0, s1 = stats[0], stats[1]
        if len(stats) >= 2 and s0.mean is not None and s1.mean is not None:
            diff = s1.mean - s0.mean
            if s0.sd is not None and s1.sd is not None and s0.n > 1 and s1.n > 1:
                se = math.sqrt(s0.sd**2 / s0.n + s1.sd**2 / s1.n)
                ci = (diff - _t95(s0.n + s1.n - 2) * se, diff + _t95(s0.n + s1.n - 2) * se)
        res.metrics.append(
            MetricResult(
                metric=metric,
                arms=stats,
                difference=round(diff, 4) if diff is not None else None,
                ci95=(round(ci[0], 4), round(ci[1], 4)) if ci else None,
                reading=(
                    _reading(metric, stats[0], stats[1], diff, ci, primary=metric == exp.metric)
                    if len(stats) >= 2
                    else ""
                ),
                lower_is_better=metric in LOWER_IS_BETTER,
            )
        )
    if record:
        await db.commit()
    return res
