"""Experiments API: the learner designs, starts, stops and reads n-of-1 experiments. Results are
hypotheses with raw numbers; assignments are visible per unit (no hidden scores)."""

from typing import Any

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DB, Learner
from app.db.models import Experiment, ExperimentAssignment, SkillNode
from app.kernel import experiments
from app.schemas.experiments import (
    ArmOut,
    ArmStatsOut,
    ExperimentIn,
    ExperimentList,
    ExperimentOut,
    MetricOut,
    ResultsOut,
    TemplateIn,
)

router = APIRouter(prefix="/experiments", tags=["experiments"])


async def _out(db: AsyncSession, exp: Experiment) -> ExperimentOut:
    arms = await experiments.arms_of(db, exp.id)
    counts: dict[str, int] = {a.id: 0 for a in arms}
    stmt = select(ExperimentAssignment.arm_id).where(ExperimentAssignment.experiment_id == exp.id)
    for arm_id in (await db.execute(stmt)).scalars():
        counts[arm_id] = counts.get(arm_id, 0) + 1
    return ExperimentOut(
        id=exp.id,
        name=exp.name,
        hypothesis=exp.hypothesis,
        metric=exp.metric,
        unit_type=exp.unit_type,
        status=exp.status,
        created_at=exp.created_at,
        started_at=exp.started_at,
        ended_at=exp.ended_at,
        arms=[
            ArmOut(id=a.id, name=a.name, config=dict(a.config_json), assigned=counts[a.id])
            for a in arms
        ],
    )


@router.get(
    "", summary="Experiments, templates and available metrics", response_model=ExperimentList
)
async def list_experiments(db: DB, learner: Learner) -> ExperimentList:
    rows = await experiments.list_all(db, learner.id)
    return ExperimentList(
        experiments=[await _out(db, e) for e in rows],
        templates=[{"id": k, **v} for k, v in experiments.TEMPLATES.items()],
        metrics=list(experiments.METRICS),
    )


@router.post(
    "", summary="Create an experiment by hand", response_model=ExperimentOut, status_code=201
)
async def create(body: ExperimentIn, db: DB, learner: Learner) -> ExperimentOut:
    exp = await experiments.create(
        db,
        learner.id,
        name=body.name,
        hypothesis=body.hypothesis,
        metric=body.metric,
        unit_type=body.unit_type,
        arms=[a.model_dump() for a in body.arms],
    )
    return await _out(db, exp)


@router.post(
    "/from-template",
    summary="Create from a template (e.g. socratic-vs-explicit)",
    response_model=ExperimentOut,
    status_code=201,
)
async def from_template(body: TemplateIn, db: DB, learner: Learner) -> ExperimentOut:
    return await _out(db, await experiments.from_template(db, learner.id, body.template))


@router.post(
    "/{experiment_id}/start",
    summary="Start: new units get assigned from now on",
    response_model=ExperimentOut,
)
async def start(experiment_id: str, db: DB, learner: Learner) -> ExperimentOut:
    return await _out(db, await experiments.start(db, learner.id, experiment_id))


@router.post(
    "/{experiment_id}/stop",
    summary="Stop: freeze the window; results stay readable",
    response_model=ExperimentOut,
)
async def stop(experiment_id: str, db: DB, learner: Learner) -> ExperimentOut:
    return await _out(db, await experiments.stop(db, learner.id, experiment_id))


@router.get(
    "/{experiment_id}/results",
    summary="Per-arm outcomes from the event log, read as hypotheses",
    response_model=ResultsOut,
)
async def results(experiment_id: str, db: DB, learner: Learner, record: bool = False) -> ResultsOut:
    res = await experiments.results(db, learner.id, experiment_id, record=record)
    stmt = select(ExperimentAssignment).where(ExperimentAssignment.experiment_id == experiment_id)
    arm_names = {a.id: a.name for a in res.arms}
    units: list[dict[str, Any]] = []
    for a in (await db.execute(stmt)).scalars():
        label = a.unit_id
        if a.unit_type == "node":
            node = await db.get(SkillNode, a.unit_id)
            label = node.title if node else a.unit_id
        units.append({"id": a.unit_id, "arm": arm_names.get(a.arm_id), "label": label, "ts": a.ts})
    return ResultsOut(
        experiment=await _out(db, res.experiment),
        primary_metric=res.experiment.metric,
        metrics=[
            MetricOut(
                metric=m.metric,
                lower_is_better=m.lower_is_better,
                arms=[
                    ArmStatsOut(
                        arm_id=s.arm_id,
                        name=s.name,
                        n=s.n,
                        mean=s.mean,
                        sd=s.sd,
                        n_units=s.n_units,
                        n_events=s.n_events,
                        fidelity=s.fidelity,
                    )
                    for s in m.arms
                ],
                difference=m.difference,
                ci95=list(m.ci95) if m.ci95 else None,
                reading=m.reading,
                available=m.available,
                method=m.method,
            )
            for m in res.metrics
        ],
        units=units,
        analysis_version=res.analysis_version,
        units_without_data=res.units_without_data,
        low_fidelity_units=res.low_fidelity_units,
        outcome_window_days=res.outcome_window_days,
        caveats=res.caveats,
    )
