"""Activation receipts retain valid membership through edits, restore and wipe."""

import json
import sqlite3

import pytest

from alembic import command
from app.db.activation_ddl import ACTIVATION_GUARDS, ACTIVATION_REVISION
from app.db.backup import BackupError, _check_after_upgrade, _check_snapshot_schema
from app.db.migrate import alembic_config
from app.db.portability import export_learner, wipe_learner
from tests._rows import fill_all_tables


def _database(tmp_path):
    path = tmp_path / "activation.db"
    url = f"sqlite:///{path}"
    command.upgrade(alembic_config(url), "head")
    rows = fill_all_tables(url)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys=ON")
    return path, url, conn, rows


def test_receipt_immutable_and_membership_survives_edits(tmp_path):
    path, _, conn, rows = _database(tmp_path)
    skill = rows["skill_node"]["id"]
    owner = rows["learner_profile"]["id"]
    clone = dict(rows["skill_node"], id="outside", slug="outside")
    with conn:
        cols = ",".join(clone)
        placeholders = ",".join("?" for _ in clone)
        conn.execute(
            f"INSERT INTO skill_node({cols}) VALUES ({placeholders})",
            tuple(json.dumps(v) if isinstance(v, (list, dict)) else v for v in clone.values()),
        )
    for sql in [
        "UPDATE lesson_activation SET payload_json='{}'",
        "UPDATE lesson_activation_object SET entity_id=entity_id",
        "UPDATE learning_object SET skill_id='outside'",
        "UPDATE assessment SET skill_id='outside'",
        "UPDATE skill_edge SET to_skill_id='outside'",
        "DELETE FROM lesson_activation_skill",
    ]:
        with pytest.raises(sqlite3.IntegrityError), conn:
            conn.execute(sql)
    # Link a second same-owner skill: reparent within the receipt remains supported.
    with conn:
        conn.execute(
            "INSERT INTO lesson_activation_skill(id,learner_id,activation_id,entity_id) "
            "VALUES ('second',?,?, 'outside')",
            (owner, rows["lesson_activation"]["id"]),
        )
        conn.execute("UPDATE learning_object SET skill_id='outside'")
        conn.execute("UPDATE assessment SET skill_id='outside'")
        conn.execute("UPDATE skill_edge SET to_skill_id='outside'")
        conn.execute("UPDATE skill_node SET title='Edited' WHERE id=?", (skill,))
    _check_after_upgrade(path)
    _check_snapshot_schema(path, ACTIVATION_REVISION)
    exported = export_learner(conn, owner)
    assert len(exported["lesson_activation_skill"]) == 2
    assert (
        exported["lesson_activation"][0]["payload_json"]
        == rows["lesson_activation"]["payload_json"]
    )
    conn.close()


def test_owner_scope_and_wipe(tmp_path):
    path, url, conn, rows = _database(tmp_path)
    other = fill_all_tables(url, seq=2)
    with pytest.raises(sqlite3.IntegrityError), conn:
        conn.execute(
            "INSERT INTO lesson_activation_skill(id,learner_id,activation_id,entity_id) "
            "VALUES ('foreign',?,?,?)",
            (
                rows["learner_profile"]["id"],
                rows["lesson_activation"]["id"],
                other["skill_node"]["id"],
            ),
        )
    wipe_learner(conn, rows["learner_profile"]["id"])
    assert conn.execute("SELECT count(*) FROM lesson_activation").fetchone()[0] == 1
    assert (
        conn.execute("SELECT learner_id FROM lesson_activation").fetchone()[0]
        == other["learner_profile"]["id"]
    )
    assert not conn.execute("PRAGMA foreign_key_check").fetchall()
    _check_after_upgrade(path)
    conn.close()


def test_restore_checks_guard_definitions_and_existing_memberships(tmp_path):
    path, _, conn, _ = _database(tmp_path)
    name = "activation_object_reparent"
    with conn:
        conn.execute(f"DROP TRIGGER {name}")
        conn.execute(f"CREATE TRIGGER {name} BEFORE UPDATE ON learning_object BEGIN SELECT 1; END")
    with pytest.raises(BackupError, match="altered activation guards"):
        _check_snapshot_schema(path, ACTIVATION_REVISION)
    with conn:
        conn.execute(f"DROP TRIGGER {name}")
        conn.execute(ACTIVATION_GUARDS[name])
        # Simulate a preexisting corrupt snapshot, without weakening production checks.
        conn.execute("DROP TRIGGER activation_skill_delete_object")
        conn.execute("DROP TRIGGER activation_skill_delete_assessment")
        conn.execute("DROP TRIGGER activation_skill_delete_edge")
        conn.execute("DELETE FROM lesson_activation_skill")
    with pytest.raises(BackupError, match="invalid private content"):
        _check_after_upgrade(path)
    conn.close()


def test_populated_downgrade_refuses_before_removing_guards(tmp_path):
    _, url, conn, _ = _database(tmp_path)
    with pytest.raises(RuntimeError, match="populated activation history"):
        command.downgrade(alembic_config(url), "52443d30fac9")
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
    assert set(ACTIVATION_GUARDS) <= names
    conn.close()


def test_header_identity_and_link_insert_constraints(tmp_path):
    _, url, conn, rows = _database(tmp_path)
    foreign = fill_all_tables(url, seq=2)
    receipt = rows["lesson_activation"]
    owner = rows["learner_profile"]["id"]

    def insert_row(table, values):
        conn.execute(
            f"INSERT INTO {table}({','.join(values)}) VALUES ({','.join('?' for _ in values)})",
            tuple(values.values()),
        )

    for change in [
        {"id": "duplicate", "request_key": "new"},  # same promotion
        {"id": "duplicate", "promotion_id": foreign["lesson_promotion"]["id"]},
        {"id": "duplicate", "request_key": "new", "learner_id": foreign["learner_profile"]["id"]},
    ]:
        with pytest.raises(sqlite3.IntegrityError), conn:
            insert_row("lesson_activation", dict(receipt, **change))
    for kind, entity in [
        ("object", "learning_object"),
        ("assessment", "assessment"),
        ("edge", "skill_edge"),
    ]:
        # Remove the other receipt's link, so entity uniqueness cannot mask membership rejection.
        with conn:
            conn.execute(
                f"DELETE FROM lesson_activation_{kind} WHERE learner_id=?",
                (foreign["learner_profile"]["id"],),
            )
        with pytest.raises(sqlite3.IntegrityError), conn:
            insert_row(
                f"lesson_activation_{kind}",
                {
                    "id": "bad",
                    "learner_id": owner,
                    "activation_id": receipt["id"],
                    "entity_id": foreign[entity]["id"],
                },
            )
    conn.close()
