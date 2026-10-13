"""Storage and restored snapshots must enforce the same private ownership contract."""

import sqlite3

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from alembic import command
from app.db.backup import BackupError, _check_after_upgrade, _check_snapshot_schema
from app.db.content_ddl import CONTENT_GUARD_REVISION, CONTENT_GUARDS
from app.db.migrate import alembic_config
from app.db.models import (
    Assessment,
    LearnerProfile,
    LearningObject,
    Representation,
    SkillEdge,
    SkillNode,
)


async def test_storage_guards_and_allowed_relationships(db, learner):
    db.add(LearnerProfile(id="other", display_name="Other"))
    await db.flush()
    for name, owner in [
        ("shared", None),
        ("own", learner.id),
        ("own2", learner.id),
        ("foreign", "other"),
    ]:
        db.add(SkillNode(id=name, slug=name, title=name, domain="ai_ml", owner_learner_id=owner))
    await db.flush()
    for name in ["shared", "own", "own2", "foreign"]:
        db.add(LearningObject(id=name, skill_id=name, concept=name, goal=name))
    await db.flush()
    db.add(Representation(id="view", object_id="own", kind="analogy", content="Private"))
    db.add(
        Assessment(
            id="assessment", skill_id="own", owner_learner_id=learner.id, kind="mcq", item_json={}
        )
    )
    db.add(SkillEdge(id="edge", from_skill_id="shared", to_skill_id="own"))
    db.add(SkillEdge(id="same-owner", from_skill_id="own", to_skill_id="own2"))
    await db.commit()
    forbidden = [
        "UPDATE skill_node SET owner_learner_id=NULL WHERE id='own'",
        "UPDATE skill_node SET owner_learner_id='other' WHERE id='own'",
        "UPDATE skill_node SET owner_learner_id='other' WHERE id='shared'",
        "UPDATE learning_object SET skill_id='shared' WHERE id='own'",
        "UPDATE representation SET object_id='foreign' WHERE id='view'",
        "UPDATE assessment SET owner_learner_id=NULL WHERE id='assessment'",
        "UPDATE assessment SET skill_id='foreign' WHERE id='assessment'",
        "UPDATE skill_edge SET from_skill_id='foreign' WHERE id='edge'",
        "UPDATE skill_edge SET to_skill_id='shared' WHERE id='same-owner'",
        "INSERT INTO skill_edge(id,from_skill_id,to_skill_id,kind,weight) VALUES ('bad','foreign','own','related',1)",
        "INSERT INTO assessment(id,skill_id,kind,item_json,created_at) VALUES ('bad','own','mcq','{}','now')",
    ]
    for sql in forbidden:
        with pytest.raises(IntegrityError):
            async with db.begin_nested():
                await db.execute(text(sql))
    with pytest.raises(IntegrityError):
        async with db.begin_nested():
            await db.execute(
                text(
                    "UPDATE assessment SET skill_id='shared', owner_learner_id=NULL WHERE id='assessment'"
                )
            )
    await db.execute(text("UPDATE assessment SET skill_id='shared' WHERE id='assessment'"))
    with pytest.raises(IntegrityError):
        async with db.begin_nested():
            await db.execute(
                text("UPDATE assessment SET owner_learner_id=NULL WHERE id='assessment'")
            )
    # Same-owner reparenting and ordinary content edits do not change visibility.
    await db.execute(text("UPDATE learning_object SET skill_id='own2' WHERE id='own'"))
    await db.execute(text("UPDATE representation SET object_id='own2' WHERE id='view'"))
    await db.execute(text("UPDATE skill_node SET title='Edited' WHERE id='own'"))
    await db.commit()


def test_migration_and_backup_guard_definitions(tmp_path):
    path = tmp_path / "guards.db"
    cfg = alembic_config(f"sqlite:///{path}")
    command.upgrade(cfg, "41332c2fe9b8")
    _check_snapshot_schema(path, "41332c2fe9b8")
    command.upgrade(cfg, "head")
    _check_snapshot_schema(path, CONTENT_GUARD_REVISION)
    _check_after_upgrade(path)
    with sqlite3.connect(path) as conn:
        conn.execute("DROP TRIGGER skill_owner_immutable")
        conn.execute(
            "CREATE TRIGGER skill_owner_immutable BEFORE UPDATE ON skill_node BEGIN SELECT 1; END"
        )
    with pytest.raises(BackupError, match="altered private content guards"):
        _check_snapshot_schema(path, CONTENT_GUARD_REVISION)
    with sqlite3.connect(path) as conn:
        conn.execute("DROP TRIGGER skill_owner_immutable")
        conn.execute(CONTENT_GUARDS["skill_owner_immutable"])
    command.downgrade(cfg, "41332c2fe9b8")
    _check_snapshot_schema(path, "41332c2fe9b8")
    command.upgrade(cfg, "head")
    _check_snapshot_schema(path, CONTENT_GUARD_REVISION)


@pytest.mark.parametrize("relationship", ["assessment", "edge"])
def test_migration_and_restore_refuse_existing_invalid_relationships(tmp_path, relationship):
    from tests._rows import fill_all_tables

    path = tmp_path / "invalid.db"
    url = f"sqlite:///{path}"
    cfg = alembic_config(url)
    command.upgrade(cfg, "41332c2fe9b8")
    first = fill_all_tables(url, seq=1)
    second = fill_all_tables(url, seq=2)
    with sqlite3.connect(path) as conn:
        if relationship == "assessment":
            conn.execute("UPDATE assessment SET owner_learner_id=NULL")
        else:
            conn.execute(
                "UPDATE skill_edge SET to_skill_id=? WHERE id=?",
                (second["skill_node"]["id"], first["skill_edge"]["id"]),
            )
    with pytest.raises(RuntimeError, match="Invalid private content relationships"):
        command.upgrade(cfg, "head")
    with sqlite3.connect(path) as conn:
        assert (
            conn.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "41332c2fe9b8"
        )
        assert not conn.execute(
            "SELECT 1 FROM sqlite_master WHERE name='skill_owner_immutable'"
        ).fetchone()
    with pytest.raises(BackupError, match="invalid private content relationships"):
        _check_after_upgrade(path)


def test_populated_downgrade_preserves_ownership_guards(tmp_path):
    from tests._rows import fill_all_tables

    path = tmp_path / "downgrade.db"
    url = f"sqlite:///{path}"
    cfg = alembic_config(url)
    command.upgrade(cfg, "head")
    fill_all_tables(url)
    with pytest.raises(RuntimeError, match="private skills"):
        command.downgrade(cfg, "41332c2fe9b8")
    _check_snapshot_schema(path, CONTENT_GUARD_REVISION)


def test_downgrade_refuses_private_assessments_on_shared_skills(tmp_path):
    from tests._rows import fill_all_tables

    path = tmp_path / "assessment-only.db"
    url = f"sqlite:///{path}"
    cfg = alembic_config(url)
    # This revision predates private skills but already permits private assessments.
    command.upgrade(cfg, "30221b1ed8a7")
    fill_all_tables(url)
    command.upgrade(cfg, "head")
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT owner_learner_id FROM skill_node").fetchone()[0] is None
        assert conn.execute("SELECT owner_learner_id FROM assessment").fetchone()[0] is not None
    with pytest.raises(RuntimeError, match="private assessments"):
        command.downgrade(cfg, "41332c2fe9b8")
    _check_snapshot_schema(path, CONTENT_GUARD_REVISION)
