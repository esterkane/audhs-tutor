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
from datetime import UTC, datetime, timedelta
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
        "hypothesis": (
            "Shorter new-material blocks raise block completion "
            "(delayed recall is not attributable per session)."
        ),
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
    n: int  # = n_units (kept for older readers)
    mean: float | None  # mean of the per-unit means
    sd: float | None  # across units
    n_units: int = 0  # independent assigned units with data for this metric
    n_events: int = 0  # raw events behind them (shown, never used as the sample size)
    unit_means: list[float] = field(default_factory=list)
    fidelity: float | None = None  # share of explained turns that delivered the arm


@dataclass
class MetricResult:
    metric: str
    arms: list[ArmStats]
    difference: float | None  # arm[1] − arm[0]
    ci95: tuple[float, float] | None
    reading: str  # literal hypothesis wording
    lower_is_better: bool
    available: bool = True  # False: this unit type cannot measure the metric
    method: str = "insufficient"  # newcombe_wilson_units | welch_t_units | difference_only | …


@dataclass
class Results:
    experiment: Experiment
    arms: list[ExperimentArm]
    assignments: dict[str, int]
    metrics: list[MetricResult] = field(default_factory=list)
    analysis_version: str = "v2"
    units_without_data: int = 0
    low_fidelity_units: int = 0
    outcome_window_days: int = 30
    caveats: list[str] = field(default_factory=list)


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
_T95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306,
        9: 2.262, 10: 2.228, 12: 2.179, 15: 2.131, 20: 2.086, 25: 2.060, 30: 2.042}  # fmt: skip
Z95 = 1.959964
ANALYSIS_VERSION = "v2"  # v1 (Stage 4): per-event values, event counts as n, t-interval on events
OUTCOME_WINDOW_DAYS = (
    30  # after Stop: delayed reviews / evidence for assigned units count this long
)
MIN_UNITS_FOR_SUPPORT = 10  # independent assigned units per arm before a direction is stated
LOW_FIDELITY = 0.5  # a unit whose explained turns delivered the arm less than half the time
MIN_FIDELITY_TURNS = 2  # one cancelled stream or one slip must not exclude a unit
BINARY_METRICS = {"delayed_recall", "error_rate", "completion", "voluntary_continuation"}
# what each unit type can measure: block and session events are not per node
UNAVAILABLE_FOR_UNIT: dict[str, dict[str, str]] = {
    "node": {
        "completion": "block_ended is per block, not per node",
        "voluntary_continuation": "session length is not attributable to one node",
    },
    "session": {
        "delayed_recall": "a delayed review happens in a later session than the one that taught the item",
        "transfer": "transfer evidence lands in a later session than the one that taught the item",
    },
}


def _t95(df: float) -> float:
    """Two-sided 95 % t critical value from a small table; fractional df round *down* (the more
    conservative row); → 1.96 for large df."""
    if df < 1:
        return 12.706
    key = math.floor(df)
    for k in sorted(_T95):
        if key <= k:
            return _T95[k]
    return 1.96


def _ts(value: str) -> datetime:
    """Stored timestamps are UTC ISO strings (`utcnow_iso`); a naive string is read as UTC."""
    dt = datetime.fromisoformat(value)
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _mean_sd(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    mean = sum(values) / len(values)
    if len(values) < 2:
        return mean, None
    var = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return mean, math.sqrt(var)


def wilson(successes: float, n: int, z: float = Z95) -> tuple[float, float]:
    """Wilson score interval for a proportion; non-degenerate at 0/n and n/n (all-success)."""
    if n <= 0:
        return 0.0, 1.0
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def newcombe_diff(
    s1: float, n1: int, s2: float, n2: int
) -> tuple[float, tuple[float, float]] | None:
    """Newcombe (1998) hybrid score CI for p2 − p1. Uses unit-level proportions, so ten reviews
    of one node are one observation, and 3/3 successes is *not* a zero-width interval."""
    if n1 <= 0 or n2 <= 0:
        return None
    p1, p2 = s1 / n1, s2 / n2
    l1, u1 = wilson(s1, n1)
    l2, u2 = wilson(s2, n2)
    d = p2 - p1
    lo = d - math.sqrt((p2 - l2) ** 2 + (u1 - p1) ** 2)
    hi = d + math.sqrt((u2 - p2) ** 2 + (p1 - l1) ** 2)
    return d, (max(-1.0, lo), min(1.0, hi))


def welch_diff(a: list[float], b: list[float]) -> tuple[float, tuple[float, float] | None] | None:
    """Welch t-interval for mean(b) − mean(a) on unit means (needs ≥ 2 units per arm)."""
    ma, sa = _mean_sd(a)
    mb, sb = _mean_sd(b)
    if ma is None or mb is None:
        return None
    d = mb - ma
    if sa is None or sb is None:
        return d, None
    va, vb = sa * sa / len(a), sb * sb / len(b)
    se = math.sqrt(va + vb)
    if se == 0:
        return d, None  # no spread at all: an interval would claim certainty it has not earned
    df = (va + vb) ** 2 / (
        (va * va / (len(a) - 1) if len(a) > 1 else 0)
        + (vb * vb / (len(b) - 1) if len(b) > 1 else 0)
    )
    t = _t95(df)
    return d, (d - t * se, d + t * se)


def _unit_of_event(exp: Experiment, e: LearningEvent) -> str | None:
    if exp.unit_type == "session":
        return e.session_id
    if e.verb == "evidenced":  # competency evidence carries the skill in the result
        skill = (e.result_json or {}).get("skill_id")
        return str(skill) if skill else None
    ctx = e.context_json or {}
    node = ctx.get("node_id")
    return str(node) if node else None


@dataclass
class UnitOutcome:
    """Everything one assigned unit contributed: raw event values per metric plus arm fidelity."""

    unit_id: str
    arm_id: str
    assigned_at: str = ""
    values: dict[str, list[float]] = field(default_factory=dict)
    explained: int = 0  # tutor turns on this unit with a fidelity verdict
    delivered: int = 0  # of which actually delivered the arm (`explained.context.arm_delivered`)
    not_applied: int = 0  # turns where the mastery gate refused the arm's representation

    @property
    def fidelity(self) -> float | None:
        return self.delivered / self.explained if self.explained else None

    @property
    def low_fidelity(self) -> bool:
        return self.explained >= MIN_FIDELITY_TURNS and (self.fidelity or 0.0) < LOW_FIDELITY

    def add(self, metric: str, value: float) -> None:
        self.values.setdefault(metric, []).append(value)


def _within_window(exp: Experiment, ts: str) -> bool:
    if exp.ended_at is None:
        return True
    return _ts(ts) <= _ts(exp.ended_at) + timedelta(days=OUTCOME_WINDOW_DAYS)


def _after_stop(exp: Experiment, ts: str) -> bool:
    return exp.ended_at is not None and _ts(ts) > _ts(exp.ended_at)


async def unit_outcomes(
    db: AsyncSession, learner_id: str, exp: Experiment
) -> dict[str, UnitOutcome]:
    """Per assigned unit: event values per metric, joined through the unit's assignment and
    counted only from the moment the unit was assigned. Learning events count while the experiment
    runs; delayed reviews and evidence for already-assigned units keep counting for
    OUTCOME_WINDOW_DAYS after Stop — that delay *is* the outcome. Nothing is counted twice; a unit
    with no events contributes nothing."""
    stmt = select(ExperimentAssignment).where(ExperimentAssignment.experiment_id == exp.id)
    units = {
        a.unit_id: UnitOutcome(unit_id=a.unit_id, arm_id=a.arm_id, assigned_at=a.ts)
        for a in (await db.execute(stmt)).scalars()
    }
    unavailable = UNAVAILABLE_FOR_UNIT.get(exp.unit_type, {})
    ev_stmt = (
        select(LearningEvent)
        .where(
            LearningEvent.learner_id == learner_id,
            LearningEvent.verb.in_(
                ("reviewed", "attempted", "block_ended", "evidenced", "explained")
            ),
        )
        .order_by(LearningEvent.ts)
    )
    if exp.started_at:
        ev_stmt = ev_stmt.where(LearningEvent.ts >= exp.started_at)
    events = list((await db.execute(ev_stmt)).scalars())
    active: dict[str, float] = {}
    for e in events:
        unit = units.get(_unit_of_event(exp, e) or "")
        if unit is None:
            continue
        if unit.assigned_at and _ts(e.ts) < _ts(unit.assigned_at):
            continue  # learned before the arm applied: not an outcome of the arm
        r = e.result_json or {}
        c = e.context_json or {}
        if e.verb in ("reviewed", "evidenced"):
            if not _within_window(exp, e.ts):
                continue
        elif _after_stop(exp, e.ts):
            continue  # learning after Stop is not part of the treatment
        if e.verb == "explained":
            if c.get("arm_delivered") is None:
                continue  # no verdict (pre-fidelity turn or cancelled stream): neither for nor against
            unit.explained += 1
            unit.delivered += 1 if c.get("arm_delivered") else 0
            unit.not_applied += 1 if c.get("arm_not_applied") else 0
        elif e.verb == "reviewed" and r.get("rating") is not None:
            if "delayed_recall" in unavailable:
                continue
            # only *delayed* reviews count: the grader's same-session FSRS update is not recall
            if float(r.get("days_since_learned") or 0.0) >= 1.0:
                unit.add("delayed_recall", 1.0 if int(r["rating"]) >= 3 else 0.0)
        elif e.verb == "attempted":
            if r.get("correct") is not None:
                unit.add("error_rate", 0.0 if r["correct"] else 1.0)
            if r.get("latency_ms") is not None:
                unit.add("latency_ms", float(r["latency_ms"]))
        elif e.verb == "block_ended" and exp.unit_type == "session":
            unit.add("completion", 0.0 if r.get("switched_early") else 1.0)
            if r.get("actual_min") is not None:
                active[unit.unit_id] = active.get(unit.unit_id, 0.0) + float(r["actual_min"])
        elif e.verb == "evidenced" and r.get("dimension") == "transfer":
            if "transfer" in unavailable:
                continue
            unit.add("transfer", float(r.get("score") or 0.0))
    if exp.unit_type == "session" and units:
        # voluntary continuation = *active* time (sum of ended blocks' measured minutes) beyond
        # the plan; an open tab with nothing ended adds nothing
        sessions = list(
            (
                await db.execute(
                    select(Session).where(
                        Session.learner_id == learner_id,
                        Session.ended_at.is_not(None),
                        Session.id.in_(list(units)),
                    )
                )
            ).scalars()
        )
        for sess in sessions:
            unit = units[sess.id]
            planned = sum(int(b.get("planned_min", 0)) for b in (sess.planned_blocks_json or []))
            if planned <= 0 or sess.id not in active:
                continue  # no plan or no measured activity: nothing to compare
            unit.add("voluntary_continuation", 1.0 if active[sess.id] > planned else 0.0)
    return units


async def outcomes(
    db: AsyncSession, learner_id: str, exp: Experiment
) -> dict[str, dict[str, list[float]]]:
    """metric → arm_id → per-event values (kept for inspection; the analysis uses unit means)."""
    out: dict[str, dict[str, list[float]]] = {m: {} for m in METRICS}
    for u in (await unit_outcomes(db, learner_id, exp)).values():
        for metric, vals in u.values.items():
            out[metric].setdefault(u.arm_id, []).extend(vals)
    return out


def _arm_stats(arm: ExperimentArm, units: list[UnitOutcome], metric: str) -> ArmStats:
    with_data = [u for u in units if u.values.get(metric)]
    unit_means = [sum(u.values[metric]) / len(u.values[metric]) for u in with_data]
    mean, sd = _mean_sd(unit_means)
    fid = [u.fidelity for u in units if u.fidelity is not None]
    return ArmStats(
        arm_id=arm.id,
        name=arm.name,
        n=len(with_data),
        n_units=len(with_data),
        n_events=sum(len(u.values[metric]) for u in with_data),
        mean=mean,
        sd=sd,
        unit_means=unit_means,
        fidelity=(sum(fid) / len(fid)) if fid else None,
    )


def _reading(
    metric: str,
    a: ArmStats,
    b: ArmStats,
    diff: float | None,
    ci: tuple[float, float] | None,
    *,
    primary: bool = False,
    excluded: int = 0,
) -> str:
    """Literal wording. The direction is stated as *which arm has the higher/lower number*; whether
    that agrees with the hypothesis is for the reader to compare with the hypothesis text."""
    label = metric.replace("_", " ")
    if a.mean is None or b.mean is None or diff is None:
        return "Not enough data yet for this metric."
    units_txt = f"{a.n_units}+{b.n_units} units ({a.n_events}+{b.n_events} events)"
    ci_txt = (
        f"; 95% CI {ci[0]:+.3f} to {ci[1]:+.3f}"
        if ci
        else "; no interval (too little data or no spread)"
    )
    excl = f" {excluded} unit(s) without the delivered arm are left out." if excluded else ""
    if metric in DIRECTIONLESS:
        return (
            f"{label}: {a.name} {a.mean:.2f} vs {b.name} {b.mean:.2f} "
            f"(difference {diff:+.3f}{ci_txt}; {units_txt}). Neither direction is 'better' here.{excl}"
        )
    small = min(a.n_units, b.n_units) < MIN_UNITS_FOR_SUPPORT
    clear = ci is not None and (ci[0] > 0 or ci[1] < 0)
    ahead = b.name if (diff < 0) == (metric in LOWER_IS_BETTER) else a.name
    if not clear:
        return (
            f"No clear difference yet on {label} (difference {diff:+.3f}{ci_txt}; {units_txt}). "
            f"Keep going or stop: your call.{excl}"
        )
    if small:
        return (
            f"{ahead} has the better number on {label} so far (difference {diff:+.3f}{ci_txt}; "
            f"{units_txt}). Fewer than {MIN_UNITS_FOR_SUPPORT} units per arm: this is not evidence "
            f"for either arm and can still flip.{excl}"
        )
    if primary:
        return (
            f"Clear difference so far: {ahead} is ahead on {label} (difference {diff:+.3f}{ci_txt}; "
            f"{units_txt}). Compare this with the hypothesis text above — it may agree with it or "
            f"contradict it.{excl}"
        )
    return (
        f"Clear difference on {label}: {ahead} is ahead (difference {diff:+.3f}{ci_txt}; "
        f"{units_txt}). Secondary metric: on its own it does not test the hypothesis.{excl}"
    )


async def results(
    db: AsyncSession, learner_id: str, experiment_id: str, *, record: bool = False
) -> Results:
    """Analysis v2: the assigned unit is the observation. Binary metrics → unit proportions,
    Newcombe/Wilson interval; continuous metrics → Welch t on unit means. Units whose explained
    turns (≥ MIN_FIDELITY_TURNS) delivered the arm less than half the time are excluded and counted."""
    exp = await get(db, learner_id, experiment_id)
    arms = await arms_of(db, exp.id)
    units = await unit_outcomes(db, learner_id, exp)
    counts: dict[str, int] = {a.id: 0 for a in arms}
    for u in units.values():
        counts[u.arm_id] = counts.get(u.arm_id, 0) + 1
    low_ids = {u.unit_id for u in units.values() if u.low_fidelity}
    low_fidelity = [units[i] for i in low_ids]
    kept = [u for u in units.values() if u.unit_id not in low_ids]
    res = Results(
        experiment=exp,
        arms=arms,
        assignments={a.name: counts[a.id] for a in arms},
        analysis_version=ANALYSIS_VERSION,
        units_without_data=sum(1 for u in units.values() if not u.values),
        low_fidelity_units=len(low_fidelity),
        outcome_window_days=OUTCOME_WINDOW_DAYS,
        caveats=[],
    )
    # another experiment of the other unit type whose run overlapped this one confounds the turns
    other_type = "session" if exp.unit_type == "node" else "node"
    for other in await list_all(db, learner_id):
        if other.id == exp.id or other.unit_type != other_type or not other.started_at:
            continue
        starts = max(_ts(other.started_at), _ts(exp.started_at)) if exp.started_at else None
        ends = min(
            _ts(other.ended_at) if other.ended_at else datetime.now(UTC),
            _ts(exp.ended_at) if exp.ended_at else datetime.now(UTC),
        )
        if starts is not None and starts <= ends:
            res.caveats.append(
                f"'{other.name}' ({other.unit_type}-unit experiment) ran at the same time; its arm "
                "can change the same turns. Read differences as confounded."
            )
    if low_fidelity:
        res.caveats.append(
            f"{len(low_fidelity)} unit(s) received the assigned arm in less than half of their "
            "tutor turns (e.g. the model explained instead of asking); they are excluded."
        )
        if any(u.not_applied for u in low_fidelity):
            res.caveats.append(
                "Some excluded turns were refused by the mastery gate (problem-first needs mastery "
                "≥ 0.6): low-mastery nodes drop out of that arm more often — a mastery confound."
            )
    single = [u for u in units.values() if u.explained == 1 and u.delivered == 0]
    if single:
        res.caveats.append(
            f"{len(single)} unit(s) have a single tutor turn that did not deliver the arm; they are "
            "kept (one turn is not a pattern) but read with care."
        )
    res.caveats.append(
        "Reading results repeatedly makes a chance difference more likely to look clear at some "
        "point; the wording stays at hypothesis level on purpose."
    )
    events = EventWriter(db, _ctx(learner_id)) if record else None
    unavailable = UNAVAILABLE_FOR_UNIT.get(exp.unit_type, {})
    for metric in METRICS:
        if metric in unavailable:
            res.metrics.append(
                MetricResult(
                    metric=metric,
                    arms=[_arm_stats(a, [], metric) for a in arms],
                    difference=None,
                    ci95=None,
                    reading=f"Not measurable for {exp.unit_type}-unit experiments: {unavailable[metric]}.",
                    lower_is_better=metric in LOWER_IS_BETTER,
                    available=False,
                    method="unavailable",
                )
            )
            continue
        stats = [_arm_stats(a, [u for u in kept if u.arm_id == a.id], metric) for a in arms]
        if events is not None:
            for st in stats:
                if st.mean is None:
                    continue
                db.add(
                    ExperimentObservation(
                        learner_id=learner_id,
                        experiment_id=exp.id,
                        arm_id=st.arm_id,
                        metric=metric,
                        value=st.mean,
                        n=st.n_units,
                    )
                )
                await events.emit(
                    Verb.MEASURED,
                    ObjectType.EXPERIMENT,
                    exp.id,
                    result={
                        "arm": st.name,
                        "metric": metric,
                        "value": round(st.mean, 4),
                        "n": st.n_units,
                        "n_units": st.n_units,
                        "n_events": st.n_events,
                    },
                    context={"experiment_id": exp.id, "analysis_version": ANALYSIS_VERSION},
                )
        diff: float | None = None
        ci: tuple[float, float] | None = None
        method = "insufficient"
        if len(stats) >= 2 and stats[0].mean is not None and stats[1].mean is not None:
            s0, s1 = stats[0], stats[1]
            if metric in BINARY_METRICS:
                nd = newcombe_diff(sum(s0.unit_means), s0.n_units, sum(s1.unit_means), s1.n_units)
                if nd is not None:
                    diff, ci = nd
                    method = "newcombe_wilson_units"
            else:
                wd = welch_diff(s0.unit_means, s1.unit_means)
                if wd is not None:
                    diff, ci = wd
                    method = "welch_t_units" if ci else "difference_only"
        excluded_here = len([u for u in low_fidelity if u.values.get(metric)])
        res.metrics.append(
            MetricResult(
                metric=metric,
                arms=stats,
                difference=round(diff, 4) if diff is not None else None,
                ci95=(round(ci[0], 4), round(ci[1], 4)) if ci else None,
                reading=(
                    _reading(
                        metric,
                        stats[0],
                        stats[1],
                        diff,
                        ci,
                        primary=metric == exp.metric,
                        excluded=excluded_here if metric == exp.metric else 0,
                    )
                    if len(stats) >= 2
                    else ""
                ),
                lower_is_better=metric in LOWER_IS_BETTER,
                available=True,
                method=method,
            )
        )
    if record:
        await db.commit()
    return res
