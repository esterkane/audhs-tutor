import sqlite3

import pytest

from alembic import command
from app.db.backup import create_backup, restore_backup
from app.db.migrate import alembic_config, upgrade_to_head
from app.db.portability import wipe_learner
from app.db.session import sync_connect
from tests._rows import dump_tables, fill_all_tables


@pytest.mark.parametrize("scope", ["learner", "full"])
def test_request_backup_restore_and_scoped_wipe(tmp_path, scope):
    url = f"sqlite:///{tmp_path / 'source.db'}"
    upgrade_to_head(url)
    owner = fill_all_tables(url)
    other = fill_all_tables(url, seq=2)
    before = dump_tables(url)["visual_generation_request"]
    archive = tmp_path / "backup.zip"
    create_backup(url, archive, scope=scope)
    destination = tmp_path / "restored"
    restore_backup(archive, destination)
    restored = f"sqlite:///{destination / 'data' / 'dev.db'}"
    assert dump_tables(restored)["visual_generation_request"] == before
    with sync_connect(restored) as conn:
        wipe_learner(conn, owner["learner_profile"]["id"])
        left = conn.execute("SELECT learner_id FROM visual_generation_request").fetchall()
        assert left == [(other["learner_profile"]["id"],)]
        assert not conn.execute("PRAGMA foreign_key_check").fetchall()


def test_populated_generation_downgrade_refuses_before_ddl(tmp_path):
    url = f"sqlite:///{tmp_path / 'source.db'}"
    upgrade_to_head(url)
    fill_all_tables(url)
    before = dump_tables(url)
    with pytest.raises(RuntimeError, match="Refusing to discard visual generation"):
        command.downgrade(alembic_config(url), "0a507010540e")
    assert dump_tables(url) == before


def test_empty_generation_roundtrip(tmp_path):
    path = tmp_path / "empty.db"
    url = f"sqlite:///{path}"
    upgrade_to_head(url)
    command.downgrade(alembic_config(url), "0a507010540e")
    upgrade_to_head(url)
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT count(*) FROM visual_generation_request").fetchone()[0] == 0
