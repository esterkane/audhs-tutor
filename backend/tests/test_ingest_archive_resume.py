import zipfile
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DocumentVersion
from app.knowledge.ingest import service


@pytest.mark.parametrize("failures", [1, 2])
async def test_resume_retries_only_failed_archive_members(
    db: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failures: int
) -> None:
    archive = tmp_path / "bundle.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("stable.md", "# Stable\n\nKeep this completed material.")
        z.writestr("retry.md", "# Retry\n\nRecover this material after a temporary failure.")
    real = service.ingest_file
    calls: list[str] = []

    async def flaky(*args: Any, **kwargs: Any) -> Any:
        nonlocal failures
        name = args[1].name
        calls.append(name)
        if name == "retry.md" and failures:
            failures -= 1
            raise OSError("Synthetic temporary storage failure")
        return await real(*args, **kwargs)

    monkeypatch.setattr(service, "ingest_file", flaky)
    report = await service.ingest_path(db, tmp_path, options=service.IngestOptions(media=False))
    assert len(report.skipped) == 1 and report.skipped[0].outcome == "retryable_error"
    while report.skipped:
        calls.clear()
        report = await service.ingest_path(
            db, tmp_path, options=service.IngestOptions(media=False), resume_run_id=report.run_id
        )
        assert calls == ["retry.md"]
    assert [r.uri.rsplit("/", 1)[-1] for r in report.results] == ["retry.md"]
    assert (await db.execute(select(func.count(DocumentVersion.id)))).scalar_one() == 2
    # An old failed record must not cause another retry once a later attempt succeeded.
    calls.clear()
    final = await service.ingest_path(
        db, tmp_path, options=service.IngestOptions(media=False), resume_run_id=report.run_id
    )
    assert not calls and not final.results and not final.skipped
    assert final.resumed == 1
