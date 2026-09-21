"""Background ingest runs inside this process (course-material stage 1). No job service: one
asyncio task per run plus a live snapshot the API can poll. The durable record is `ingest_run`;
this is only the in-memory view of the run that is happening now."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import new_id, utcnow_iso
from app.db.models import IngestRun
from app.knowledge.ingest.runtime import default_options
from app.knowledge.ingest.service import IngestProgress, IngestReport, ingest_path

log = logging.getLogger(__name__)
KEEP_FINISHED = 5  # finished jobs kept for polling before older ones are dropped
SHUTDOWN_GRACE_S = 15.0


@dataclass
class IngestJob:
    job_id: str
    request: dict[str, Any]  # the validated request as a dict (path, course, trust_tier, …)
    path: Path
    status: str = "queued"  # queued | running | finished | interrupted | failed
    started_at: str = field(default_factory=utcnow_iso)
    finished_at: str | None = None
    run_id: str | None = None
    progress: IngestProgress | None = None
    report: IngestReport | None = None
    error: str | None = None
    stop: bool = False
    task: asyncio.Task[None] | None = None

    @property
    def active(self) -> bool:
        return self.status in ("queued", "running")


def jobs_of(app: Any) -> dict[str, IngestJob]:
    jobs: dict[str, IngestJob] | None = getattr(app.state, "ingest_jobs", None)
    if jobs is None:
        jobs = {}
        app.state.ingest_jobs = jobs
    return jobs


def prune(jobs: dict[str, IngestJob]) -> None:
    """Keep the active job and the last few finished ones; a finished job carries its whole
    report, so the map must not grow without bound."""
    finished = sorted((j for j in jobs.values() if not j.active), key=lambda j: j.started_at)
    for j in finished[:-KEEP_FINISHED]:
        jobs.pop(j.job_id, None)


async def resume_options(db: AsyncSession, run_id: str) -> dict[str, Any]:
    """The options an interrupted run was started with — a resume must keep them (trust tier,
    source type, media, language) or the same course ends up split across trust tiers."""
    previous = await db.get(IngestRun, run_id)
    if previous is None:
        raise KeyError(run_id)
    if previous.status != "interrupted":
        raise ValueError(previous.status)
    return {"course": previous.course, **dict(previous.options_json or {})}


def start(app: Any, request: dict[str, Any], path: Path) -> IngestJob:
    jobs = jobs_of(app)
    prune(jobs)
    job = IngestJob(job_id=new_id(), request=request, path=path)
    jobs[job.job_id] = job
    job.task = asyncio.create_task(run_ingest_job(app, job))
    return job


async def run_ingest_job(app: Any, job: IngestJob) -> None:
    """The task body: its own DB session and repo, progress into the job, outcome into the job."""
    req = job.request
    factory = app.state.session_factory
    job.status = "running"
    repo = None
    own_repo = False
    try:
        async with factory() as db:
            if req.get("index", True):
                from app.knowledge.reindex import build_repo

                repo = getattr(app.state, "repo", None)
                if repo is None:
                    repo = await build_repo(db, app.state.settings)
                    own_repo = True
            options = await default_options(
                db,
                app.state.settings,
                media=bool(req.get("media", True)),
                language=req.get("language"),
            )

            def on_progress(p: IngestProgress) -> None:
                job.progress = p
                job.run_id = p.run_id

            options.progress = on_progress
            options.should_stop = lambda: job.stop
            report = await ingest_path(
                db,
                job.path,
                course=req.get("course"),
                source_type=req.get("source_type"),
                trust_tier=int(req.get("trust_tier", 2)),
                repo=repo,
                options=options,
                resume_run_id=req.get("resume_run_id"),
            )
            job.run_id = report.run_id
            job.report = report
            job.status = "interrupted" if report.interrupted else "finished"
    except asyncio.CancelledError:
        job.status = "interrupted"
        raise
    except Exception as e:  # the job must not vanish: the error is the result
        job.status = "failed"
        job.error = f"{type(e).__name__}: {e}"[:500]
        log.exception("ingest job %s failed", job.job_id)
    finally:
        job.finished_at = utcnow_iso()
        if own_repo and repo is not None and hasattr(repo, "client"):
            try:
                await repo.client.close()
            except Exception:  # noqa: BLE001
                pass


async def stop_all(app: Any, grace_s: float = SHUTDOWN_GRACE_S) -> None:
    """On shutdown: ask running jobs to stop after the current file and wait a little, so the
    run is recorded `interrupted` (resumable) instead of staying `running` forever."""
    tasks = [j.task for j in jobs_of(app).values() if j.active and j.task and not j.task.done()]
    for j in jobs_of(app).values():
        j.stop = True
    if tasks:
        await asyncio.wait(tasks, timeout=grace_s)
        for t in tasks:
            if not t.done():
                t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
