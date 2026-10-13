"""Whole-schema regressions for indirect ownership and atomic guard restoration."""

import sqlite3

import pytest

from app.db.ddl import LEARNING_EVENT_GUARDS
from app.db.migrate import upgrade_to_head
from app.db.portability import export_learner, wipe_learner
from app.db.session import sync_connect
from tests._rows import dump_tables, fill_all_tables


@pytest.fixture
def database(tmp_path):
    url = f"sqlite:///{tmp_path / 'wipe.db'}"
    upgrade_to_head(url)
    first = fill_all_tables(url, seq=1)
    second = fill_all_tables(url, seq=2)
    return url, first, second


def test_complete_export_and_wipe_includes_indirect_rows_without_affecting_other_owner(database):
    url, first, second = database
    owner = first["learner_profile"]["id"]
    other = second["learner_profile"]["id"]
    with sync_connect(url) as conn:
        # This fixture intentionally exercises shared curriculum, independent of private skills.
        from app.db.content_ddl import CONTENT_GUARDS

        conn.execute("DROP TRIGGER skill_owner_immutable")
        conn.execute("UPDATE skill_node SET owner_learner_id=NULL")
        conn.execute(CONTENT_GUARDS["skill_owner_immutable"])
        # A representation without an attributable model call on shared content remains shared.
        row = first["representation"]
        conn.execute(
            "INSERT INTO representation (id, object_id, kind, content, model_call_id, "
            "cached, created_at, provenance_json) VALUES (?, ?, ?, ?, NULL, 1, ?, '{}')",
            ("shared", row["object_id"], "explanation", "Shared content", row["created_at"]),
        )
        conn.commit()
        prior_other = export_learner(conn, other)
        before = export_learner(conn, owner)
        assert before["representation"][0]["id"] == first["representation"]["id"]
        assert before["experiment_arm"][0]["id"] == first["experiment_arm"]["id"]
        deleted = wipe_learner(conn, owner)
        assert deleted["representation"] == deleted["experiment_arm"] == 1
        assert deleted["authored_visual_document"] == deleted["authored_visual_version"] == 1
        assert deleted["authored_visual_review"] == deleted["authored_visual_operation"] == 1
        assert deleted["authored_visual_source_snapshot"] == 1
        assert all(not rows for rows in export_learner(conn, owner).values())
        assert export_learner(conn, other) == prior_other
        for table in ("chunk", "document", "learning_object"):
            assert conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 2
        assert (
            conn.execute("SELECT content FROM representation WHERE id='shared'").fetchone()[0]
            == "Shared content"
        )
        assert not conn.execute("PRAGMA foreign_key_check").fetchall()
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("DELETE FROM learning_event")
        # Repeating a completed wipe does not affect anyone else.
        assert all(count == 0 for count in wipe_learner(conn, owner).values())
        assert export_learner(conn, other) == prior_other


def test_failed_wipe_rolls_back_rows_and_guard_ddl(database):
    url, first, _ = database
    with sync_connect(url) as conn:
        conn.execute(
            "CREATE TRIGGER fail_wipe BEFORE DELETE ON model_call "
            "BEGIN SELECT RAISE(ABORT, 'synthetic failure'); END"
        )
        conn.commit()
        before = dump_tables(url)
        with pytest.raises(sqlite3.IntegrityError, match="synthetic failure"):
            wipe_learner(conn, first["learner_profile"]["id"])
        assert dump_tables(url) == before
        guards = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
        }
        assert set(LEARNING_EVENT_GUARDS) <= guards
        assert not conn.execute("PRAGMA foreign_key_check").fetchall()
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("UPDATE learning_event SET verb=verb")
