"""Private lineage persistence and blocked shared publication; no production writer yet."""

import json
import sqlite3

import pytest

from alembic import command
from app.core.errors import AppError
from app.db import backup
from app.db.lesson_ddl import LESSON_IMMUTABLE_GUARDS
from app.db.migrate import alembic_config, upgrade_to_head
from app.db.portability import export_learner, wipe_learner
from app.db.session import make_engine, make_session_factory, sync_connect
from app.kernel import curriculum
from tests._rows import dump_tables, fill_all_tables


@pytest.fixture
def stored(tmp_path):
    path = tmp_path / "lesson.db"
    url = f"sqlite:///{path}"
    upgrade_to_head(url)
    rows = fill_all_tables(url)
    return path, url, rows


@pytest.mark.parametrize("scope", ["learner", "full"])
def test_lesson_lineage_backup_and_wipe(stored, tmp_path, scope):
    path, url, rows = stored
    before = dump_tables(url)
    archive = tmp_path / "backup.zip"
    backup.create_backup(url, archive, scope=scope)
    dest = tmp_path / "restored"
    backup.restore_backup(archive, dest)
    after = dump_tables(f"sqlite:///{dest / 'data/dev.db'}")
    assert after["lesson_promotion"] == before["lesson_promotion"]
    assert after["lesson_promotion_snapshot"] == (
        before["lesson_promotion_snapshot"] if scope == "full" else []
    )
    with sqlite3.connect(dest / "data/dev.db") as conn:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute("UPDATE lesson_promotion SET fingerprint='changed'")
    with sync_connect(url) as conn:
        owner = rows["learner_profile"]["id"]
        assert export_learner(conn, owner)["lesson_promotion"]
        for table in LESSON_IMMUTABLE_GUARDS:
            with pytest.raises(sqlite3.IntegrityError, match="immutable"):
                conn.execute(f"UPDATE {table} SET id=id")
        wipe_learner(conn, owner)
        assert conn.execute("SELECT count(*) FROM lesson_promotion").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM lesson_promotion_snapshot").fetchone()[0] == 0


async def test_private_promotion_cannot_publish_shared_curriculum(stored):
    path, url, rows = stored
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE curriculum_draft SET status='draft'")
    before = dump_tables(url)
    engine = make_engine(f"sqlite+aiosqlite:///{path}")
    try:
        async with make_session_factory(engine)() as db:
            with pytest.raises(AppError, match="remains private"):
                await curriculum.publish_draft(
                    db, rows["learner_profile"]["id"], rows["curriculum_draft"]["id"]
                )
    finally:
        await engine.dispose()
    assert dump_tables(url) == before


def test_owned_foreign_keys_and_downgrade(stored):
    _, url, rows = stored
    with sync_connect(url) as conn:

        def insert(table, row):
            columns = list(row)
            conn.execute(
                f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
                [
                    json.dumps(row[c]) if isinstance(row[c], (dict, list)) else row[c]
                    for c in columns
                ],
            )

        insert("learner_profile", {**rows["learner_profile"], "id": "other-owner"})
        insert(
            "curriculum_draft",
            {
                **rows["curriculum_draft"],
                "id": "other-draft",
                "learner_id": "other-owner",
                "area_id": None,
            },
        )
        row = {
            **rows["lesson_promotion"],
            "id": "other-promotion",
            "draft_id": "other-draft",
            "request_key": "other-request",
        }
        # Real foreign draft, then real foreign answer; both pairs must match ownership.
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            insert("lesson_promotion", row)
        row["learner_id"] = "other-owner"
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            insert("lesson_promotion", row)
        insert(
            "tutor_answer",
            {
                **rows["tutor_answer"],
                "id": "other-answer",
                "learner_id": "other-owner",
                "session_id": None,
            },
        )
        row["answer_id"] = "other-answer"
        insert("lesson_promotion", row)
    before = dump_tables(url)
    with sync_connect(url) as conn:
        revision = conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    with pytest.raises(
        RuntimeError,
        match="populated provisional feedback history",
    ):
        command.downgrade(alembic_config(url), "c0ff66df480b")
    assert dump_tables(url) == before
    with sync_connect(url) as conn:
        assert conn.execute("SELECT version_num FROM alembic_version").fetchone()[0] == revision
        for table in LESSON_IMMUTABLE_GUARDS:
            with pytest.raises(sqlite3.IntegrityError, match="immutable"):
                conn.execute(f"UPDATE {table} SET id=id")
        wipe_learner(conn, rows["learner_profile"]["id"])
        wipe_learner(conn, "other-owner")
    command.downgrade(alembic_config(url), "c0ff66df480b")
    assert "lesson_promotion" not in dump_tables(url)
    upgrade_to_head(url)
    assert dump_tables(url)["lesson_promotion"] == []


def test_lesson_history_guard_at_its_own_revision(tmp_path):
    """Later guards must not mask removal of the original lineage downgrade guard."""
    url = f"sqlite:///{tmp_path / 'pinned-lesson.db'}"
    config = alembic_config(url)
    command.upgrade(config, "30221b1ed8a7")
    fill_all_tables(url)
    before = dump_tables(url)
    with pytest.raises(RuntimeError, match="populated private lesson history"):
        command.downgrade(config, "c0ff66df480b")
    assert dump_tables(url) == before
    with sync_connect(url) as conn:
        assert (
            conn.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "30221b1ed8a7"
        )
