"""Models settings API: the registry as a screen. Pull and bench run as background jobs (one at a
time per model) whose progress lines are readable; the registry status shows where things stand."""

import asyncio
from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter, Request
from ulid import ULID

from app.api.deps import DB, BudgetDep, Learner, SettingsDep
from app.core.errors import AppError
from app.db.models import ModelRegistry
from app.models_ai import manage, registry, usage
from app.schemas.models_admin import (
    AddIn,
    AssignIn,
    ChainEntry,
    CostsOut,
    HfSearchHit,
    HfSearchOut,
    JobList,
    JobOut,
    ModelList,
    ModelRow,
    RouteRow,
    RoutingOut,
)

router = APIRouter(prefix="/models", tags=["models"])


@dataclass
class Job:
    id: str
    kind: str
    registry_id: str
    status: str = "running"
    log: list[str] = field(default_factory=list)
    error: str | None = None
    result: dict[str, Any] | None = None
    task: asyncio.Task[None] | None = None

    def out(self) -> JobOut:
        return JobOut(
            id=self.id,
            kind=self.kind,
            registry_id=self.registry_id,
            status=self.status,
            log=self.log[-20:],
            error=self.error,
            result=self.result,
        )


def _jobs(request: Request) -> dict[str, Job]:
    jobs: dict[str, Job] | None = getattr(request.app.state, "model_jobs", None)
    if jobs is None:
        jobs = {}
        request.app.state.model_jobs = jobs
    return jobs


def _row(r: ModelRegistry) -> ModelRow:
    return ModelRow(
        id=r.id,
        display_name=r.display_name,
        source=r.source,
        repo_id=r.repo_id,
        file_or_tag=r.file_or_tag,
        runtime=r.runtime,
        role=r.role,
        quant=r.quant,
        size_gb=r.size_gb,
        context_len=r.context_len,
        licence=r.licence,
        status=r.status,
        benchmark=r.benchmark_json,
        price_in_per_mtok=r.price_in_per_mtok,
        price_out_per_mtok=r.price_out_per_mtok,
        local_path=r.local_path,
        updated_at=r.updated_at,
    )


@router.get(
    "", summary="Registry rows (defaults seeded, readiness refreshed)", response_model=ModelList
)
async def list_models(db: DB, settings: SettingsDep) -> ModelList:
    await manage.seed(db, settings)
    return ModelList(models=[_row(r) for r in await registry.list_models(db)])


@router.get(
    "/search",
    summary="Search Hugging Face (GGUF / mlx-community filters)",
    response_model=HfSearchOut,
)
async def search(q: str, gguf: bool = False, mlx: bool = False, limit: int = 20) -> HfSearchOut:
    hits = await manage.search(q, gguf=gguf, mlx=mlx, limit=min(limit, 50))
    return HfSearchOut(
        hits=[
            HfSearchHit(
                repo_id=h["repo_id"],
                downloads=h.get("downloads"),
                likes=h.get("likes"),
                tags=list(h.get("tags") or []),
            )
            for h in hits
        ]
    )


@router.post("", summary="Add a registry row (nothing is downloaded yet)", response_model=ModelRow)
async def add(body: AddIn, db: DB, settings: SettingsDep) -> ModelRow:
    return _row(await manage.add(db, settings, **body.model_dump()))


def _start_job(request: Request, kind: str, registry_id: str, settings: Any) -> Job:
    jobs = _jobs(request)
    for j in jobs.values():
        if j.registry_id == registry_id and j.status == "running":
            raise AppError("busy", f"{kind} already running for {registry_id}", http_status=409)
    job = Job(id=str(ULID()), kind=kind, registry_id=registry_id)
    factory = request.app.state.session_factory

    async def run() -> None:
        try:
            async with factory() as db:
                if kind == "pull":
                    await manage.pull(db, settings, registry_id, job.log.append)
                else:
                    job.result = await manage.bench(db, settings, registry_id, job.log.append)
            job.status = "done"
        except Exception as e:
            job.status, job.error = "failed", f"{type(e).__name__}: {e}"

    job.task = asyncio.create_task(run())
    jobs[job.id] = job
    finished = [j for j in jobs.values() if j.status != "running"]
    for old in finished[:-20]:  # keep the last 20 finished jobs readable
        jobs.pop(old.id, None)
    return job


@router.post(
    "/{registry_id}/pull",
    summary="Download in the background (status: downloading → ready)",
    response_model=JobOut,
    status_code=202,
)
async def pull(registry_id: str, request: Request, db: DB, settings: SettingsDep) -> JobOut:
    await registry.get_row(db, registry_id)  # 404 when unknown
    return _start_job(request, "pull", registry_id, settings).out()


@router.post(
    "/{registry_id}/bench",
    summary="Benchmark in the background (tok/s, first token, tutoring checks)",
    response_model=JobOut,
    status_code=202,
)
async def bench(registry_id: str, request: Request, db: DB, settings: SettingsDep) -> JobOut:
    row = await registry.get_row(db, registry_id)
    if row.status != "ready":
        raise AppError(
            "not_ready", f"{registry_id} is {row.status}; pull it first", http_status=400
        )
    return _start_job(request, "bench", registry_id, settings).out()


@router.get(
    "/jobs", summary="Background pull/bench jobs with their progress lines", response_model=JobList
)
async def jobs(request: Request) -> JobList:
    return JobList(jobs=[j.out() for j in _jobs(request).values()])


@router.post(
    "/{registry_id}/assign",
    summary="Route a TaskClass to this model for the owner (must be ready)",
    response_model=RoutingOut,
)
async def assign(
    registry_id: str, body: AssignIn, db: DB, learner: Learner, settings: SettingsDep
) -> RoutingOut:
    await manage.assign(db, learner.id, body.task, registry_id)
    return await routing(db, learner, settings)


@router.delete(
    "/{registry_id}",
    summary="Remove the artefact and mark the row removed",
    response_model=ModelRow,
)
async def remove(registry_id: str, db: DB, settings: SettingsDep) -> ModelRow:
    return _row(await manage.remove(db, settings, registry_id))


@router.get(
    "/routing",
    summary="TaskClass → chain with readiness; what each task will actually use",
    response_model=RoutingOut,
)
async def routing(db: DB, learner: Learner, settings: SettingsDep) -> RoutingOut:
    rows = await manage.routing_table(db, settings, learner.id)
    return RoutingOut(
        profile=settings.routing_profile,
        routes=[
            RouteRow(
                task=r["task"],
                override=r["override"],
                chain=[ChainEntry(**c) for c in r["chain"]],
                resolved=r["resolved"],
                problem=r.get("problem"),
                action=r.get("action"),
            )
            for r in rows
        ],
    )


@router.get(
    "/costs",
    summary="Cost view: daily cap, reported/estimated/unknown/legacy spend, per task/provider, failures",
    response_model=CostsOut,
)
async def costs(db: DB, budget: BudgetDep, days: int = 1) -> CostsOut:
    rep = await usage.cost_report(db, budget, days=max(1, min(days, 90)))
    return CostsOut(**usage.report_dict(rep))
