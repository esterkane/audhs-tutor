"""Persistence/recovery foundation only; no public write API or review semantics yet."""

import sqlite3
import zipfile

import pytest
from sqlalchemy import create_engine, update
from sqlalchemy.exc import IntegrityError

from alembic import command
from app.db import backup, models
from app.db.base import Base
from app.db.migrate import alembic_config, upgrade_to_head
from app.db.portability import export_learner, wipe_learner
from app.db.session import sync_connect
from app.db.visual_ddl import VISUAL_IMMUTABLE_GUARDS
from tests._rows import dump_tables, fill_all_tables


@pytest.fixture
def visual_database(tmp_path):
    path = tmp_path / "visual.db"
    url = f"sqlite:///{path}"
    upgrade_to_head(url)
    rows = fill_all_tables(url)
    return path, url, rows


def test_every_history_record_is_immutable_but_document_archive_is_reversible(visual_database):
    path, _, _ = visual_database
    with sqlite3.connect(path) as conn:
        for table in VISUAL_IMMUTABLE_GUARDS:
            with pytest.raises(sqlite3.IntegrityError, match="immutable"):
                conn.execute(f"UPDATE {table} SET id=id")
        before = conn.execute("SELECT count(*) FROM authored_visual_version").fetchone()[0]
        conn.execute("UPDATE authored_visual_document SET archived=1")
        conn.execute("UPDATE authored_visual_document SET archived=0")
        assert conn.execute("SELECT archived FROM authored_visual_document").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM authored_visual_version").fetchone()[0] == before


@pytest.mark.parametrize("scope", ["learner", "full"])
def test_visual_backup_retains_content_reviews_and_distinguishes_missing_snapshot(
    visual_database, tmp_path, scope
):
    _, url, rows = visual_database
    before = dump_tables(url)
    archive = tmp_path / f"{scope}.zip"
    result = backup.create_backup(url, archive, scope=scope)
    destination = tmp_path / f"restored-{scope}"
    backup.restore_backup(archive, destination)
    after = dump_tables(f"sqlite:///{destination / 'data' / 'dev.db'}")
    for table in (
        "authored_visual_document",
        "authored_visual_version",
        "authored_visual_review",
        "authored_visual_operation",
    ):
        assert after[table] == before[table]
    if scope == "full":
        assert after["authored_visual_source_snapshot"] == before["authored_visual_source_snapshot"]
    else:
        assert after["authored_visual_source_snapshot"] == []
        assert "raw authored-visual generation snapshots" in " ".join(result.manifest["excluded"])
        assert "Missing visual grounding" in (destination / "RESTORE-NOTES.md").read_text()
        with zipfile.ZipFile(archive) as z:
            # VACUUM must remove deleted raw snapshot bytes too, not only its row.
            sentinel = rows["authored_visual_source_snapshot"]["snapshot_json"].encode()
            assert sentinel not in z.read(backup.DB_MEMBER)
    assert dump_tables(url) == before
    with sqlite3.connect(destination / "data" / "dev.db") as conn:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute("UPDATE authored_visual_version SET version=2")


def test_export_wipe_covers_all_visual_tables_only_for_selected_learner(visual_database, tmp_path):
    _, url, rows = visual_database
    other = fill_all_tables(url, seq=2)
    owner = rows["learner_profile"]["id"]
    other_id = other["learner_profile"]["id"]
    # Scope fixture to visual history and shared corpus. The all-table fixture also
    # exposes older Representation/experiment-arm wipe problems, documented separately.
    scoped_url = f"sqlite:///{tmp_path / 'scoped.db'}"
    upgrade_to_head(scoped_url)
    engine = create_engine(scoped_url)
    wanted = {
        "learner_profile",
        "document",
        "document_version",
        "chunk",
        "authored_visual_document",
        *VISUAL_IMMUTABLE_GUARDS,
    }
    with engine.begin() as connection:
        for table in Base.metadata.sorted_tables:
            if table.name in wanted:
                for dataset in (rows, other):
                    connection.execute(table.insert().values(**dataset[table.name]))
    engine.dispose()
    with sync_connect(scoped_url) as conn:
        prior_other = export_learner(conn, other_id)
        exported = export_learner(conn, owner)
        tables = {"authored_visual_document", *VISUAL_IMMUTABLE_GUARDS}
        assert all(len(exported[table]) == 1 for table in tables)
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        deleted = wipe_learner(conn, owner)
        assert all(deleted[table] == 1 for table in tables)
        assert export_learner(conn, other_id) == prior_other
        assert conn.execute("SELECT count(*) FROM chunk").fetchone()[0] == 2
        assert not conn.execute("PRAGMA foreign_key_check").fetchall()


def test_migration_refuses_populated_downgrade_without_partial_deletion(visual_database):
    _, url, _ = visual_database
    before = dump_tables(url)
    with pytest.raises(RuntimeError, match="Cannot discard authored visual history"):
        command.downgrade(alembic_config(url), "f6e5b241a148")
    assert dump_tables(url) == before


def test_empty_upgrade_downgrade_and_upgrade_preserves_existing_tables(tmp_path):
    path = tmp_path / "empty.db"
    url = f"sqlite:///{path}"
    upgrade_to_head(url)
    command.downgrade(alembic_config(url), "f6e5b241a148")
    upgrade_to_head(url)
    with sqlite3.connect(path) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "tutor_answer_fts" in tables
        assert set(VISUAL_IMMUTABLE_GUARDS) <= tables


@pytest.mark.parametrize("table", list(VISUAL_IMMUTABLE_GUARDS))
def test_restore_rejects_missing_immutable_guard(visual_database, table):
    path, _, _ = visual_database
    with sqlite3.connect(path) as conn:
        conn.execute(f"DROP TRIGGER {table}_no_update")
    with pytest.raises(backup.BackupError, match="guard/index triggers"):
        backup._check_snapshot_schema(path, backup.head_revision())


async def test_composite_foreign_keys_block_cross_owner_history(db, learner):
    other = models.LearnerProfile(display_name="Other")
    db.add(other)
    await db.flush()
    doc = models.AuthoredVisualDocument(learner_id=learner.id, title="Private")
    db.add(doc)
    await db.commit()
    owner_id, other_id, document_id = learner.id, other.id, doc.id
    version = models.AuthoredVisualVersion(
        learner_id=other_id,
        document_id=document_id,
        version=1,
        spec_json="{}",
        content_sha256="a" * 64,
        binding_json="{}",
        snapshot_sha256="b" * 64,
        target_kind="answer",
        target_id="missing-target",
    )
    db.add(version)
    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        await db.flush()
    await db.rollback()
    version.learner_id = owner_id
    db.add(version)
    await db.commit()
    for cls, kwargs in [
        (models.AuthoredVisualSourceSnapshot, {"version_id": version.id, "snapshot_json": "{}"}),
        (
            models.AuthoredVisualReview,
            {
                "version_id": version.id,
                "content_sha256": "a" * 64,
                "snapshot_sha256": "b" * 64,
                "decision": "accept",
            },
        ),
        (
            models.AuthoredVisualOperation,
            {
                "document_id": document_id,
                "request_id": "retry",
                "fingerprint": "hash",
                "response_json": {},
            },
        ),
    ]:
        db.add(cls(learner_id=other_id, **kwargs))
        with pytest.raises(IntegrityError, match="FOREIGN KEY"):
            await db.flush()
        await db.rollback()
    # create_all has the same guards as the migrated database.
    with pytest.raises(IntegrityError, match="immutable"):
        await db.execute(update(models.AuthoredVisualVersion).values(version=2))
    await db.rollback()


@pytest.mark.parametrize(
    "table",
    ["authored_visual_version", "authored_visual_operation", "authored_visual_source_snapshot"],
)
def test_duplicate_version_request_or_snapshot_identity_is_rejected(visual_database, table):
    path, _, _ = visual_database
    with sqlite3.connect(path) as conn:
        columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
        names = ", ".join(f'"{column}"' for column in columns)
        values = ", ".join(
            "'new-primary-id'" if column == "id" else f'"{column}"' for column in columns
        )
        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE constraint"):
            conn.execute(f"INSERT INTO {table} ({names}) SELECT {values} FROM {table}")
