"""Ownership proof only: no database mutations, models, live data or automatic recovery."""

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

from app.db.base import new_id
from app.knowledge.ingest.ownership import OwnershipUnavailable, RunOwnership


@pytest.fixture
def database(tmp_path: Path) -> Path:
    path = tmp_path / "test.db"
    path.touch()
    return path


def test_live_owner_blocks_second_acquisition_and_close_is_idempotent(database: Path) -> None:
    run = new_id()
    owner = RunOwnership.acquire(database, run, create=True)
    assert owner is not None
    with owner:
        assert RunOwnership.acquire(database, run, expected=owner.identity) is None
        with pytest.raises(OwnershipUnavailable):
            RunOwnership.acquire(database, run, create=True)
    owner.close()
    successor = RunOwnership.acquire(database, run, expected=owner.identity)
    assert successor is not None
    with successor:
        assert RunOwnership.acquire(database, run, expected=owner.identity) is None
    with pytest.raises(OwnershipUnavailable):
        with owner:
            pass


def test_missing_evidence_is_not_recreated(database: Path) -> None:
    with pytest.raises(OwnershipUnavailable):
        RunOwnership.acquire(database, new_id())
    assert not database.with_name("test.db.ingest-locks").exists()
    with pytest.raises(OwnershipUnavailable):
        RunOwnership.acquire(database, "../escape", create=True)


def test_symlink_database_alias_uses_same_lock(database: Path, tmp_path: Path) -> None:
    alias = tmp_path / "alias.db"
    alias.symlink_to(database)
    run = new_id()
    owner = RunOwnership.acquire(database, run, create=True)
    assert owner is not None
    with owner:
        assert RunOwnership.acquire(alias, run, expected=owner.identity) is None


def test_missing_or_replaced_evidence_stays_unknown(database: Path, tmp_path: Path) -> None:
    run = new_id()
    owner = RunOwnership.acquire(database, run, create=True)
    assert owner is not None
    owner.close()
    lock = database.with_name("test.db.ingest-locks") / run
    lock.unlink()  # simulate external deletion, not an allowed application action
    with pytest.raises(OwnershipUnavailable):
        RunOwnership.acquire(database, run, expected=owner.identity)
    lock.write_text("replacement")
    lock.chmod(0o600)
    with pytest.raises(OwnershipUnavailable):
        RunOwnership.acquire(database, run, expected=owner.identity)
    lock.unlink()
    target = tmp_path / "other"
    target.touch(mode=0o600)
    lock.symlink_to(target)
    with pytest.raises(OwnershipUnavailable):
        RunOwnership.acquire(database, run, expected=owner.identity)


def test_shared_directory_and_hardlinked_lock_are_rejected(database: Path, tmp_path: Path) -> None:
    run = new_id()
    owner = RunOwnership.acquire(database, run, create=True)
    assert owner is not None
    owner.close()
    directory = database.with_name("test.db.ingest-locks")
    directory.chmod(0o755)
    with pytest.raises(OwnershipUnavailable):
        RunOwnership.acquire(database, run, expected=owner.identity)
    directory.chmod(0o700)
    os.link(directory / run, tmp_path / "lock-alias")
    with pytest.raises(OwnershipUnavailable):
        RunOwnership.acquire(database, run, expected=owner.identity)


async def test_hard_exit_releases_owner_but_not_a_live_process(database: Path) -> None:
    run = new_id()
    child = """
import json, os, sys
from pathlib import Path
from app.knowledge.ingest.ownership import RunOwnership
owner = RunOwnership.acquire(Path(sys.argv[1]), sys.argv[2], create=True)
assert owner is not None
print(json.dumps(owner.identity), flush=True)
sys.stdin.readline()
os._exit(77)
"""
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-c",
        child,
        str(database),
        run,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
    )
    try:
        assert process.stdout is not None and process.stdin is not None
        identity = tuple(json.loads(await asyncio.wait_for(process.stdout.readline(), 10)))
        assert RunOwnership.acquire(database, run, expected=identity) is None
        process.stdin.write(b"exit\n")
        await process.stdin.drain()
        assert await asyncio.wait_for(process.wait(), 10) == 77
        recovered = RunOwnership.acquire(database, run, expected=identity)
        assert recovered is not None
        with recovered:
            assert RunOwnership.acquire(database, run, expected=identity) is None
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()
