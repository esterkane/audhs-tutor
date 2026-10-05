"""Ownership evidence is separate from restored SQL state; no grading is enabled here."""

import json
import os
import sqlite3
from pathlib import Path

import pytest

from app.core.local_ownership import OwnershipUnavailable
from app.db.base import new_id
from app.knowledge.ingest.ownership import RunOwnership
from app.orchestrator.assessment_guard import AssessmentGuard


def test_prepared_guard_blocks_live_owner_and_preserves_import_namespace(tmp_path: Path):
    database = tmp_path / "db.sqlite"
    database.touch()
    claim = new_id()
    guard = AssessmentGuard.create(database, claim)
    receipt = guard.receipt
    imported = RunOwnership.acquire(database, claim, create=True)
    assert imported is not None  # Separate namespace, despite identical operation IDs.
    try:
        assert AssessmentGuard.acquire_prepared(database, claim, receipt) is None
    finally:
        imported.close()
        guard.close()
    recovered = AssessmentGuard.acquire_prepared(database, claim, receipt)
    assert recovered is not None and recovered.receipt == receipt
    recovered.close()
    recovered.close()


def test_restored_prepared_database_cannot_rewind_inference_boundary(tmp_path: Path):
    database = tmp_path / "db.sqlite"
    backup = tmp_path / "snapshot.sqlite"
    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE operation (phase TEXT, receipt TEXT)")
    claim = new_id()
    guard = AssessmentGuard.create(database, claim)
    receipt = guard.receipt
    with sqlite3.connect(database) as db:
        db.execute("INSERT INTO operation VALUES (?, ?)", ("prepared", json.dumps(receipt)))
    with sqlite3.connect(database) as db, sqlite3.connect(backup) as snapshot:
        db.backup(snapshot)
    guard.seal_inference()
    guard.seal_inference()  # Idempotent; never truncates the seal.
    with sqlite3.connect(database) as db:
        db.execute("UPDATE operation SET phase='completed'")
    guard.close()
    with sqlite3.connect(backup) as snapshot, sqlite3.connect(database) as db:
        snapshot.backup(db)
        phase, restored = db.execute("SELECT phase, receipt FROM operation").fetchone()
    assert phase == "prepared" and json.loads(restored) == receipt
    with pytest.raises(OwnershipUnavailable, match="entered inference"):
        AssessmentGuard.acquire_prepared(database, claim, receipt)


@pytest.mark.parametrize("damage", ["missing", "token", "truncated", "extra", "receipt"])
def test_missing_or_malformed_evidence_never_proves_prepared(tmp_path: Path, damage: str):
    database = tmp_path / "db.sqlite"
    database.touch()
    claim = new_id()
    guard = AssessmentGuard.create(database, claim)
    receipt = guard.receipt
    guard.close()
    marker = database.with_name(database.name + ".assessment-locks") / claim
    if damage == "missing":
        marker.unlink()
    elif damage == "token":
        receipt["token"] = "0" * 32
    elif damage == "truncated":
        marker.write_bytes(b"assessment-v1:")
    elif damage == "extra":
        with marker.open("ab") as stream:
            stream.write(b"unexpected")
    else:
        receipt["version"] = True
    with pytest.raises(OwnershipUnavailable):
        AssessmentGuard.acquire_prepared(database, claim, receipt)


def test_failed_seal_sync_raises_and_does_not_restore_prepared(tmp_path: Path, monkeypatch):
    database = tmp_path / "db.sqlite"
    database.touch()
    claim = new_id()
    guard = AssessmentGuard.create(database, claim)
    receipt = guard.receipt

    def fail(_fd):
        raise OSError("sync failed")

    monkeypatch.setattr(os, "fsync", fail)
    with pytest.raises(OSError, match="sync failed"):
        guard.seal_inference()
    guard.close()
    with pytest.raises(OwnershipUnavailable):
        AssessmentGuard.acquire_prepared(database, claim, receipt)
