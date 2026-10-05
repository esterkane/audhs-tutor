"""Crash/reconcile/resume against disposable SQLite and synthetic text, never live runtimes."""

import asyncio
import sys
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import DocumentVersion, IngestRun
from app.knowledge.ingest.recovery import OWNER_KEY, reconcile_abandoned_runs
from app.knowledge.ingest.service import IngestOptions, ingest_path


async def test_live_worker_then_hard_exit_reconciles_once_and_resumes(
    client: AsyncClient,
    db_path: Path,
    tmp_path: Path,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    root = tmp_path / "materials"
    root.mkdir()
    (root / "one.md").write_text("# First\n\nA synthetic source about cleaning data.")
    (root / "two.md").write_text("# Second\n\nA distinct synthetic source about missing values.")
    child = """
import asyncio, os, sys
from pathlib import Path
from app.db.session import make_engine, make_session_factory
from app.knowledge.ingest.service import IngestOptions, ingest_path

def progress(p):
    if p.done == 1:
        print(p.run_id, flush=True)
        sys.stdin.readline()
        os._exit(77)

async def main():
    engine = make_engine('sqlite+aiosqlite:///' + sys.argv[1])
    async with make_session_factory(engine)() as db:
        await ingest_path(db, Path(sys.argv[2]), trust_tier=1, options=IngestOptions(media=False, progress=progress))
asyncio.run(main())
"""
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-c",
        child,
        str(db_path),
        str(root),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
    )
    try:
        assert process.stdout is not None and process.stdin is not None
        run_id = (await asyncio.wait_for(process.stdout.readline(), 10)).decode().strip()
        assert len(run_id) == 26
        async with session_factory() as db:
            row = await db.get(IngestRun, run_id)
            assert row is not None and row.files_done == 1
            assert OWNER_KEY in row.options_json
            row.started_at = "2000-01-01T00:00:00+00:00"  # age must never substitute for ownership
            await db.commit()
        assert await reconcile_abandoned_runs(session_factory) == 0
        process.stdin.write(b"exit\n")
        await process.stdin.drain()
        assert await asyncio.wait_for(process.wait(), 10) == 77
        results = await asyncio.gather(
            reconcile_abandoned_runs(session_factory),
            reconcile_abandoned_runs(session_factory),
        )
        assert sum(results) == 1
        runs = (await client.get("/api/corpus/ingest/runs")).json()
        assert runs[0]["id"] == run_id and runs[0]["status"] == "interrupted"
        assert runs[0]["files_done"] == 1
        async with session_factory() as db:
            original_ids = set((await db.execute(select(DocumentVersion.id))).scalars())
        assert len(original_ids) == 1
        resumed = await client.post(
            "/api/corpus/ingest/jobs",
            json={
                "path": str(root),
                "media": True,
                "index": True,
                "trust_tier": 3,
                "resume_run_id": run_id,
            },
        )
        assert resumed.status_code == 202, resumed.text
        job_id = resumed.json()["job_id"]
        for _ in range(200):
            job = (await client.get(f"/api/corpus/ingest/jobs/{job_id}")).json()
            if job["status"] not in ("running", "queued"):
                break
            await asyncio.sleep(0.01)
        assert job["status"] == "finished", job
        assert job["result"]["summary"]["resumed"] == 1
        async with session_factory() as db:
            ids = set((await db.execute(select(DocumentVersion.id))).scalars())
            assert len(ids) == 2 and original_ids <= ids
            continuation = await db.get(IngestRun, job["run_id"])
            assert continuation is not None
            assert continuation.options_json["trust_tier"] == 1
            assert continuation.options_json["media"] is False
            assert continuation.options_json["index"] is False
            assert continuation.resumed_from == run_id
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()


async def test_legacy_and_malformed_ownership_remain_unknown(
    db: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    for options in ({}, {OWNER_KEY: [True, 1]}, {OWNER_KEY: [1]}, {OWNER_KEY: [1, 2]}):
        db.add(IngestRun(src="/synthetic", status="running", options_json=options))
    await db.commit()
    assert await reconcile_abandoned_runs(session_factory) == 0
    assert (
        await db.execute(
            select(func.count())
            .select_from(IngestRun)
            .where(
                IngestRun.status == "running",
            )
        )
    ).scalar_one() == 4


async def test_two_resumes_create_only_one_continuation(
    db: AsyncSession,
    tmp_path: Path,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    root = tmp_path / "source"
    root.mkdir()
    (root / "one.md").write_text("# Synthetic\n\nA small synthetic file.")
    first = await ingest_path(
        db, root, options=IngestOptions(media=False, should_stop=lambda: True)
    )
    assert first.interrupted and first.run_id

    async def resume() -> object:
        async with session_factory() as session:
            return await ingest_path(
                session, root, options=IngestOptions(media=False), resume_run_id=first.run_id
            )

    outcomes = await asyncio.gather(resume(), resume(), return_exceptions=True)
    assert sum(not isinstance(outcome, BaseException) for outcome in outcomes) == 1
    async with session_factory() as session:
        count = (
            await session.execute(
                select(func.count())
                .select_from(IngestRun)
                .where(
                    IngestRun.resumed_from == first.run_id,
                )
            )
        ).scalar_one()
        assert count == 1


async def test_cli_resume_uses_original_no_index_before_building_repo(
    db: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import importlib.util
    from unittest.mock import AsyncMock

    from app.core.config import Settings

    root = tmp_path / "cli-source"
    root.mkdir()
    (root / "one.md").write_text("# CLI\n\nA synthetic command-line import.")
    first = await ingest_path(
        db, root, options=IngestOptions(media=False, should_stop=lambda: True)
    )
    assert first.interrupted and first.run_id
    script = (await asyncio.to_thread(Path(__file__).resolve)).parents[2] / "scripts" / "ingest.py"
    spec = importlib.util.spec_from_file_location("ingest_cli_test", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    settings = Settings(database_url=str(db.get_bind().engine.url), _env_file=None)
    monkeypatch.setattr(module, "get_settings", lambda: settings)
    monkeypatch.setattr(module, "upgrade_to_head", lambda _url: None)
    # Avoid even readiness calls from the initial form defaults: only saved options matter here.
    monkeypatch.setattr(
        module, "default_options", AsyncMock(return_value=IngestOptions(media=False))
    )
    build_repo = AsyncMock(
        side_effect=AssertionError("saved no-index run must not build retrieval")
    )
    monkeypatch.setattr(module, "build_repo", build_repo)
    monkeypatch.setattr(sys, "argv", ["ingest.py", "--src", str(root), "--resume", "--quiet"])
    assert await module.main() == 0
    build_repo.assert_not_called()


async def test_application_startup_recovers_owned_abandoned_record(
    db: AsyncSession, settings
) -> None:
    from app.db.base import new_id
    from app.knowledge.ingest.recovery import acquire_new_owner, owner_marker
    from app.main import create_app

    run_id = new_id()
    owner = acquire_new_owner(db, run_id)
    assert owner is not None
    db.add(
        IngestRun(id=run_id, src="/synthetic", status="running", options_json=owner_marker(owner))
    )
    await db.commit()
    owner.close()
    app = create_app(settings)
    app.state.providers = {}  # no runtime/model initialization needed for this lifecycle test
    async with app.router.lifespan_context(app):
        db.expire_all()
        row = await db.get(IngestRun, run_id)
        assert row is not None and row.status == "interrupted"
