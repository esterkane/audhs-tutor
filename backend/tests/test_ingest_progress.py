"""Course-material stage 1: an ingest run explains itself — per-file and per-archive-member
progress, one outcome class per file (imported / unchanged / reference_only / no_content /
unsupported / gated / retryable_error / access_blocked / parser_error), a recorded run that an
interruption leaves resumable, and a resume that never re-processes what was already terminal
(no duplicate versions, no touching originals). Synthetic fixtures only; no runtime models."""

import asyncio
import io
import json
import zipfile
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DocumentVersion, IngestRun, IngestRunItem
from app.knowledge.ingest.service import (
    IngestOptions,
    IngestProgress,
    classify,
    ingest_path,
    latest_resumable_run,
)


def _zip(files: dict[str, bytes | str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data.encode() if isinstance(data, str) else data)
    return buf.getvalue()


def _course(tmp_path: Path) -> Path:
    """<root>/Course/01 - Intro/… with every outcome class represented once."""
    sec = tmp_path / "Udemy" / "Progress Course" / "01 - Intro"
    sec.mkdir(parents=True)
    (sec / "001 - notes.md").write_text("# Attention\n\nScores are scaled by sqrt(d_k).\n")
    (sec / "002 - script.py").write_text("def softmax(x):\n    return x\n")
    (sec / "003 - external-links.json").write_text(
        json.dumps([{"title": "Paper", "url": "https://example.org/paper"}])
    )
    (sec / "004 - empty.csv").write_text("")
    (sec / "005 - book.mobi").write_bytes(b"BOOKMOBI")
    (sec / "006 - broken.docx").write_bytes(b"this is not a zip archive at all")
    (sec / "007 - lecture.mp3").write_bytes(b"ID3\x00\x00\x00")
    (sec / "008 - bundle.zip").write_bytes(
        _zip(
            {
                "bundle/readme.md": "# Bundle\n\nHello from the archive.",
                "bundle/main.py": "print(1)\n",
                "bundle/.env": "SECRET=1",
                "bundle/inner.zip": b"PK",
                "bundle/old.mobi": b"BOOKMOBI",
            }
        )
    )
    return tmp_path / "Udemy"


async def _versions(db: AsyncSession) -> int:
    return int((await db.execute(select(func.count(DocumentVersion.id)))).scalar_one())


async def test_every_outcome_class_is_named_and_counted(db: AsyncSession, tmp_path: Path) -> None:
    root = _course(tmp_path)
    seen: list[IngestProgress] = []
    report = await ingest_path(db, root, options=IngestOptions(media=False, progress=seen.append))
    by_uri = {r.uri.rsplit("/", 1)[-1]: r.outcome for r in report.results}
    by_uri.update({s.path.rsplit("/", 1)[-1]: s.outcome for s in report.skipped})
    assert by_uri["001 - notes.md"] == "imported"
    assert by_uri["002 - script.py"] == "imported"
    assert by_uri["003 - external-links.json"] == "reference_only"  # a link is not material
    assert by_uri["004 - empty.csv"] == "no_content"
    assert by_uri["005 - book.mobi"] == "unsupported"
    assert by_uri["006 - broken.docx"] == "parser_error"  # claimed docx, not a zip
    assert by_uri["007 - lecture.mp3"] == "gated"  # media off for this run
    assert by_uri["readme.md"] == "imported" and by_uri["main.py"] == "imported"
    assert by_uri[".env"] == "gated" and by_uri["inner.zip"] == "unsupported"
    assert by_uri["old.mobi"] == "unsupported"
    counts = report.summary()["outcomes"]
    assert counts["imported"] == 4 and counts["reference_only"] == 1
    assert counts["parser_error"] == 1 and counts["gated"] == 2 and counts["no_content"] == 1
    assert counts["unsupported"] == 3 and counts["retryable_error"] == 0
    # the links list is not counted as new material
    assert report.summary()["new_versions"] == 4
    # progress: every file under the root once, archive members with member counts
    assert seen[0].done == 0 and seen[0].total == 8
    assert [p.done for p in seen if p.archive is None] == list(range(8))
    members = [p for p in seen if p.archive == "008 - bundle.zip"]
    assert [m.member_done for m in members] == [0, 1, 2] and members[0].member_total == 3
    assert seen[-1].outcomes["imported"] >= 2 and seen[-1].run_id == report.run_id
    # the run is recorded with one terminal item per file and member
    run = await db.get(IngestRun, report.run_id)
    assert run is not None and run.status == "finished" and run.files_total == 8
    assert run.files_done == 8 and run.summary_json["outcomes"] == counts
    items = (
        (await db.execute(select(IngestRunItem).where(IngestRunItem.run_id == run.id)))
        .scalars()
        .all()
    )
    assert len(items) == 8 + 5  # 8 top-level files (the archive itself counts once) + 5 members
    assert {i.outcome for i in items if i.uri.endswith("notes.md")} == {"imported"}
    # imported files and members point at their document; the archive row itself does not
    imported = [i for i in items if i.outcome == "imported" and i.reason != "archive"]
    assert imported and all(i.document_id and i.version_id for i in imported)
    # a second run: everything unchanged, nothing new
    again = await ingest_path(db, root, options=IngestOptions(media=False))
    assert again.summary()["outcomes"]["unchanged"] == 4 and again.summary()["new_versions"] == 0


async def test_interrupted_run_resumes_without_duplicating_work(
    db: AsyncSession, tmp_path: Path
) -> None:
    root = _course(tmp_path)
    calls = 0

    def stop_after_three() -> bool:
        nonlocal calls
        calls += 1
        return calls > 3

    first = await ingest_path(
        db, root, options=IngestOptions(media=False, should_stop=stop_after_three)
    )
    assert first.interrupted and first.run_id
    run = await db.get(IngestRun, first.run_id)
    assert run is not None and run.status == "interrupted" and run.files_done == 3
    assert run.last_uri and run.last_uri.endswith("003 - external-links.json")
    versions_before = await _versions(db)
    assert versions_before == 3  # notes, script, links list
    resumable = await latest_resumable_run(db, root)
    assert resumable is not None and resumable.id == first.run_id
    # resume: the three terminal items are not touched again (no new versions), the rest runs
    second = await ingest_path(
        db, root, options=IngestOptions(media=False), resume_run_id=first.run_id
    )
    assert not second.interrupted and second.resumed == 3
    assert {r.uri.rsplit("/", 1)[-1] for r in second.results} >= {"readme.md", "main.py"}
    assert all(not r.uri.endswith("notes.md") for r in second.results)
    assert await _versions(db) == versions_before + 2  # only the archive members were new
    row = await db.get(IngestRun, second.run_id)
    assert row is not None and row.status == "finished" and row.resumed_from == first.run_id
    assert row.files_done == 8 and await latest_resumable_run(db, root) is None
    # resuming a finished run is a no-op run: everything is already terminal
    third = await ingest_path(
        db, root, options=IngestOptions(media=False), resume_run_id=second.run_id
    )
    assert third.resumed == 8 and not third.results and await _versions(db) == versions_before + 2
    with pytest.raises(KeyError):
        await ingest_path(db, root, options=IngestOptions(media=False), resume_run_id="nope")


async def test_cancellation_marks_the_run_interrupted(db: AsyncSession, tmp_path: Path) -> None:
    root = _course(tmp_path)

    def cancel_on_second(p: IngestProgress) -> None:
        if p.done == 1:
            raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await ingest_path(db, root, options=IngestOptions(media=False, progress=cancel_on_second))
    run = (
        (await db.execute(select(IngestRun).order_by(IngestRun.started_at.desc())))
        .scalars()
        .first()
    )
    assert run is not None and run.status == "interrupted" and run.files_done == 1
    assert await latest_resumable_run(db, root) is not None


def test_classification_of_failures() -> None:
    from app.knowledge.ingest.loaders import SkipFile
    from app.knowledge.ingest.media import SttSupportMissing
    from app.knowledge.ingest.types import RuntimeCallFailed

    assert classify(SkipFile("json: empty list")) == "no_content"
    assert classify(SkipFile("json: not a transcript or a links list")) == "unsupported"
    assert classify(ValueError("unsupported file type: .mobi (export as epub)")) == "unsupported"
    assert classify(SttSupportMissing("no ready model")) == "retryable_error"
    assert (
        classify(
            RuntimeCallFailed(task="stt", provider="mlx", registry_id="w", model="w", error="boom")
        )
        == "retryable_error"
    )
    assert classify(PermissionError(13, "denied")) == "access_blocked"
    assert classify(RuntimeError("File 'x' is encrypted, password required")) == "access_blocked"
    assert classify(OSError(5, "input/output error")) == "retryable_error"
    assert classify(RuntimeError(".mkv needs ffmpeg (brew install ffmpeg)")) == "retryable_error"
    assert (
        classify(RuntimeError("no audio decoder found: brew install ffmpeg")) == "retryable_error"
    )
    assert classify(ValueError("text file too large (60 MB)")) == "gated"
    assert classify(SkipFile("lockfile")) == "gated"
    assert classify(zipfile.BadZipFile("File is not a zip file")) == "parser_error"
    assert classify(KeyError("word/document.xml")) == "parser_error"


async def test_ingest_job_lifecycle_over_http(
    client: AsyncClient, db: AsyncSession, tmp_path: Path
) -> None:
    root = _course(tmp_path)  # tmp_path lies under INGEST_ROOTS in the test settings
    body = {"path": str(root), "media": False, "index": False, "trust_tier": 2}
    r = await client.post("/api/corpus/ingest/jobs", json=body)
    assert r.status_code == 202, r.text
    job = r.json()
    assert job["status"] in ("queued", "running") and job["result"] is None
    # a second job while one runs is refused, never queued silently
    busy = await client.post("/api/corpus/ingest/jobs", json=body)
    assert busy.status_code == 409 and busy.json()["error"]["code"] == "busy"
    for _ in range(200):
        r = await client.get(f"/api/corpus/ingest/jobs/{job['job_id']}")
        assert r.status_code == 200
        job = r.json()
        if job["status"] not in ("queued", "running"):
            break
        await asyncio.sleep(0.02)
    assert job["status"] == "finished", job
    assert job["run_id"] and job["progress"]["total"] == 8
    counts = job["result"]["summary"]["outcomes"]
    assert counts["imported"] == 4 and counts["parser_error"] == 1 and counts["gated"] == 2
    assert {s["outcome"] for s in job["result"]["skipped"]} >= {"unsupported", "parser_error"}
    assert all(res["outcome"] in ("imported", "reference_only") for res in job["result"]["results"])
    runs = (await client.get("/api/corpus/ingest/runs")).json()
    assert runs[0]["id"] == job["run_id"] and runs[0]["status"] == "finished"
    assert runs[0]["outcomes"] == counts and runs[0]["files_done"] == 8
    # resume validation: unknown run → 404, a finished run → 409
    r = await client.post("/api/corpus/ingest/jobs", json={**body, "resume_run_id": "nope"})
    assert r.status_code == 404
    r = await client.post("/api/corpus/ingest/jobs", json={**body, "resume_run_id": job["run_id"]})
    assert r.status_code == 409 and "only interrupted runs resume" in r.json()["error"]["message"]
    assert (await client.get("/api/corpus/ingest/jobs/missing")).status_code == 404


async def test_ingest_job_stop_leaves_a_resumable_run_that_resumes_over_http(
    client: AsyncClient, db: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deterministic: the job's stop check fires after exactly one file (as a cancel request
    arriving at that moment would), the run is `interrupted`, and a resume over HTTP finishes
    without redoing that file. The cancel endpoint itself is exercised too."""
    from app.knowledge.ingest import jobs as jobs_mod

    root = _course(tmp_path)
    body = {"path": str(root), "media": False, "index": False, "trust_tier": 2}
    real_ingest_path = jobs_mod.ingest_path

    async def stop_after_one(*a: object, **kw: object) -> object:
        opts = kw["options"]
        assert isinstance(opts, IngestOptions)
        seen: list[int] = []
        original_progress = opts.progress

        def progress(p: IngestProgress) -> None:
            seen.append(p.done)
            if original_progress:
                original_progress(p)

        opts.progress = progress
        opts.should_stop = lambda: bool(seen) and seen[-1] >= 1
        return await real_ingest_path(*a, **kw)  # type: ignore[arg-type]

    monkeypatch.setattr(jobs_mod, "ingest_path", stop_after_one)
    job = (await client.post("/api/corpus/ingest/jobs", json=body)).json()
    assert job["status"] in ("queued", "running")
    r = await client.post(f"/api/corpus/ingest/jobs/{job['job_id']}/cancel")
    assert r.status_code == 200
    for _ in range(200):
        job = (await client.get(f"/api/corpus/ingest/jobs/{job['job_id']}")).json()
        if job["status"] not in ("queued", "running"):
            break
        await asyncio.sleep(0.02)
    assert job["status"] == "interrupted", job
    # the stop check runs before a file starts: files 0 and 1 finished, file 2 never started;
    # the last progress snapshot is the one taken when file 1 started (done=1)
    assert job["progress"]["done"] == 1
    runs = (await client.get("/api/corpus/ingest/runs")).json()
    assert runs[0]["status"] == "interrupted" and runs[0]["files_done"] == 2
    monkeypatch.setattr(jobs_mod, "ingest_path", real_ingest_path)
    # the resume ignores the form's trust tier: the run's own settings are kept
    resumed = await client.post(
        "/api/corpus/ingest/jobs", json={**body, "trust_tier": 3, "resume_run_id": job["run_id"]}
    )
    assert resumed.status_code == 202
    j2 = resumed.json()
    for _ in range(200):
        j2 = (await client.get(f"/api/corpus/ingest/jobs/{j2['job_id']}")).json()
        if j2["status"] not in ("queued", "running"):
            break
        await asyncio.sleep(0.02)
    assert j2["status"] == "finished" and j2["result"]["summary"]["resumed"] == 2
    runs = (await client.get("/api/corpus/ingest/runs")).json()
    assert [r["status"] for r in runs[:2]] == ["finished", "resumed"]
    run_row = await db.get(IngestRun, j2["run_id"])
    assert run_row is not None and run_row.options_json["trust_tier"] == 2


async def test_real_task_cancellation_mid_run(db: AsyncSession, tmp_path: Path) -> None:
    """A genuine `task.cancel()` while the run awaits (not a hook raising synchronously)."""
    root = _course(tmp_path)
    started = asyncio.Event()

    def progress(p: IngestProgress) -> None:
        if p.done == 1:
            started.set()

    task = asyncio.create_task(
        ingest_path(db, root, options=IngestOptions(media=False, progress=progress))
    )
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    run = (
        (await db.execute(select(IngestRun).order_by(IngestRun.started_at.desc())))
        .scalars()
        .first()
    )
    assert run is not None and run.status == "interrupted"
    assert await latest_resumable_run(db, root) is not None


async def test_resume_retries_retryable_errors_but_not_other_outcomes(
    db: AsyncSession, tmp_path: Path
) -> None:
    root = _course(tmp_path)
    calls = 0

    def stop_after_all_but_archive() -> bool:
        nonlocal calls
        calls += 1
        return calls > 7

    # media on but no STT model → the mp3 is a retryable error in the first run
    first = await ingest_path(
        db, root, options=IngestOptions(media=True, should_stop=stop_after_all_but_archive)
    )
    by = {s.path.rsplit("/", 1)[-1]: s.outcome for s in first.skipped}
    assert by["007 - lecture.mp3"] == "retryable_error" and first.interrupted
    second = await ingest_path(
        db, root, options=IngestOptions(media=True), resume_run_id=first.run_id
    )
    by2 = {s.path.rsplit("/", 1)[-1]: s.outcome for s in second.skipped}
    assert "007 - lecture.mp3" in by2  # retried (still no model here), not skipped as done
    assert "005 - book.mobi" not in by2  # unsupported stays terminal
    assert second.resumed == 6  # 7 done in the first run minus the retryable one
