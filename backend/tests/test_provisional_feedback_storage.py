import sqlite3

import pytest

from app.db.migrate import upgrade_to_head
from app.db.portability import export_learner, wipe_learner
from tests._rows import fill_all_tables


@pytest.fixture
def stored(tmp_path):
    path = tmp_path / "test.db"
    url = f"sqlite:///{path}"
    upgrade_to_head(url)
    fill_all_tables(url)
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        yield conn


def test_record_is_immutable_and_claim_unique(stored):
    row = dict(stored.execute("SELECT * FROM provisional_feedback").fetchone())
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        stored.execute("UPDATE provisional_feedback SET answer='changed'")
    row["id"] = "duplicate"
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        stored.execute(
            f"INSERT INTO provisional_feedback ({','.join(row)}) VALUES ({','.join('?' for _ in row)})",
            tuple(row.values()),
        )


def test_foreign_claim_owner_rejected(stored):
    row = dict(stored.execute("SELECT * FROM provisional_feedback").fetchone())
    row.update(id="foreign", learner_id="different-owner")
    with pytest.raises(sqlite3.IntegrityError, match="ownership mismatch"):
        stored.execute(
            f"INSERT INTO provisional_feedback ({','.join(row)}) VALUES ({','.join('?' for _ in row)})",
            tuple(row.values()),
        )


def test_export_and_wipe_include_advisory_record(stored):
    owner = stored.execute("SELECT learner_id FROM provisional_feedback").fetchone()[0]
    assert len(export_learner(stored, owner)["provisional_feedback"]) == 1
    assert export_learner(stored, "another-owner")["provisional_feedback"] == []
    assert wipe_learner(stored, owner)["provisional_feedback"] == 1
    assert stored.execute("SELECT count(*) FROM provisional_feedback").fetchone()[0] == 0


def test_restore_validation_detects_rows_bypassing_insert_guard(stored):
    from app.db.provisional_ddl import INVALID_PROVISIONAL_OWNERSHIP, PROVISIONAL_GUARDS

    stored.execute("DROP TRIGGER provisional_feedback_no_update")
    # Simulate a forged archive that bypassed insert checks.
    stored.commit()
    stored.execute("PRAGMA foreign_keys=OFF")
    stored.execute("UPDATE provisional_feedback SET claim_id='missing'")
    stored.execute(PROVISIONAL_GUARDS["provisional_feedback_no_update"])
    assert stored.execute(INVALID_PROVISIONAL_OWNERSHIP).fetchone() is not None
