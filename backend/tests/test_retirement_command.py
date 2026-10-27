import asyncio
import importlib.util
import json
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.config import Settings
from app.db.models import Chunk, ChunkProvenance, Document, DocumentVersion
from app.kernel import content_retirement

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "retirement_command", ROOT / "scripts/retire_course_sources.py"
)
command = importlib.util.module_from_spec(spec)
spec.loader.exec_module(command)


async def prepared(db, db_path, tmp_path, monkeypatch, learner):
    import hashlib

    root = tmp_path / "application"
    (root / "data").mkdir(parents=True)
    course = root / "data/course.md"
    course.write_text("Excluded raw course text")
    external = tmp_path / "private-archive/original.md"
    external.parent.mkdir()
    external.write_text("Original private archive content")
    doc = Document(
        title="ExcludedPlatform course",
        source_type="markdown",
        uri=str(course),
        course="Example course",
    )
    db.add(doc)
    await db.flush()
    version = DocumentVersion(document_id=doc.id, content_hash="synthetic")
    db.add(version)
    await db.flush()
    chunk = Chunk(document_version_id=version.id, ordinal=0, text="Excluded raw course text")
    db.add(chunk)
    await db.flush()
    db.add(
        ChunkProvenance(
            chunk_id=chunk.id, source_id=doc.id, source_type="markdown", path=str(external)
        )
    )
    await db.commit()
    target = root / "data/app.db"
    with sqlite3.connect(db_path) as source:
        with sqlite3.connect(target) as copy:
            source.backup(copy)
    settings = Settings(database_url="sqlite+aiosqlite:///" + str(target), _env_file=None)
    monkeypatch.setattr(command, "get_settings", lambda: settings)
    original = content_retirement.plan

    async def plan(session):
        return await original(session, frozenset({hashlib.sha256(b"excludedplatform").hexdigest()}))

    monkeypatch.setattr(command.content_retirement, "plan", plan)
    remove = AsyncMock(return_value={"synthetic-index": 1})
    monkeypatch.setattr(command, "remove_indexed_sources", remove)
    args = SimpleNamespace(
        apply=False,
        application_root=str(root),
        receipt=str(tmp_path / "private/receipt.json"),
        backup=str(tmp_path / "private/backup.db"),
        expected_digest=None,
    )
    return args, root, course, external, remove


async def test_dry_run_then_apply_preserves_history_and_external_archive(
    db, db_path, tmp_path, monkeypatch, learner
):
    args, root, course, external, remove = await prepared(
        db, db_path, tmp_path, monkeypatch, learner
    )
    result = await command.run(args)
    assert result["mode"] == "plan" and result["chunks"] == 1 and course.is_file()
    assert not await asyncio.to_thread(Path(args.backup).exists)
    args.apply = True
    args.expected_digest = result["digest"]
    applied = await command.run(args)
    assert applied["history_preserved"] and applied["map_reset"]
    assert not course.exists() and external.read_text() == "Original private archive content"
    with sqlite3.connect(args.backup) as backup:
        assert backup.execute("select text from chunk").fetchone()[0] == "Excluded raw course text"
    with sqlite3.connect(root / "data/app.db") as current:
        assert current.execute("select text from chunk").fetchone()[0] == ""
        assert current.execute("select count(*) from knowledge_area").fetchone()[0] == 6
    replay = await command.run(args)
    assert replay["phase"] == "complete"
    remove.assert_awaited_once()


async def test_index_failure_leaves_source_content_and_can_resume(
    db, db_path, tmp_path, monkeypatch, learner
):
    args, root, course, external, remove = await prepared(
        db, db_path, tmp_path, monkeypatch, learner
    )
    args.expected_digest = (await command.run(args))["digest"]
    args.apply = True
    remove.side_effect = RuntimeError("Index unavailable")
    with pytest.raises(RuntimeError):
        await command.run(args)
    assert course.is_file()
    with sqlite3.connect(root / "data/app.db") as current:
        assert current.execute("select text from chunk").fetchone()[0] == "Excluded raw course text"
    assert json.loads(await asyncio.to_thread(Path(args.receipt).read_text))["phase"] == "backed_up"
    remove.side_effect = None
    assert (await command.run(args))["phase"] == "complete"
    assert external.exists()


async def test_wrong_digest_cannot_start_retirement(db, db_path, tmp_path, monkeypatch, learner):
    args, root, course, external, remove = await prepared(
        db, db_path, tmp_path, monkeypatch, learner
    )
    args.apply = True
    args.expected_digest = "wrong"
    with pytest.raises(ValueError):
        await command.run(args)
    assert (
        course.exists()
        and external.exists()
        and not await asyncio.to_thread(Path(args.backup).exists)
    )
    remove.assert_not_awaited()


async def test_resume_after_database_commit_and_lost_receipt(
    db, db_path, tmp_path, monkeypatch, learner
):
    args, root, course, external, remove = await prepared(
        db, db_path, tmp_path, monkeypatch, learner
    )
    args.expected_digest = (await command.run(args))["digest"]
    args.apply = True
    original = command.write_receipt
    failed = False

    def lost(path, state):
        nonlocal failed
        if state["phase"] == "database_redacted" and not failed:
            failed = True
            raise OSError("Synthetic receipt write failure after database commit")
        return original(path, state)

    monkeypatch.setattr(command, "write_receipt", lost)
    with pytest.raises(OSError):
        await command.run(args)
    assert course.is_file() and external.is_file()
    with sqlite3.connect(root / "data/app.db") as current:
        assert current.execute("select text from chunk").fetchone()[0] == ""
    assert (await command.run(args))["phase"] == "complete"
    assert not course.exists() and external.exists()
    remove.assert_awaited_once()
