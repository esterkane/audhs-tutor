"""Shared-only defaults and inherited private content access, without activation."""

import pytest
from sqlalchemy import select

from app.core.errors import AppError
from app.db.models import LearnerProfile, LearningObject, Representation, SkillNode
from app.kernel import content_access


async def test_owned_content_reads_do_not_leak_through_cached_orm_rows(db, learner):
    other = LearnerProfile(id="other", display_name="Other")
    db.add(other)
    await db.flush()
    for owner, prefix in [(None, "shared"), (learner.id, "own"), (other.id, "foreign")]:
        node = SkillNode(
            id=prefix, slug=prefix, domain="ai_ml", title=prefix, owner_learner_id=owner
        )
        db.add(node)
        await db.flush()
        obj = LearningObject(id=f"{prefix}-object", skill_id=node.id, concept=prefix, goal=prefix)
        db.add(obj)
        await db.flush()
        db.add(
            Representation(id=f"{prefix}-view", object_id=obj.id, kind="analogy", content=prefix)
        )
    await db.commit()
    for scope, allowed in [
        (None, {"shared"}),
        (learner.id, {"shared", "own"}),
        (other.id, {"shared", "foreign"}),
    ]:
        actual = set(
            await db.scalars(select(SkillNode.id).where(content_access.skill_visible(scope)))
        )
        assert actual == allowed
        for prefix in ["shared", "own", "foreign", "missing"]:
            for fn, identifier in [
                (content_access.require_skill, prefix),
                (content_access.require_object, f"{prefix}-object"),
                (content_access.require_representation, f"{prefix}-view"),
            ]:
                if prefix in allowed:
                    assert (await fn(db, scope, identifier)).id == identifier
                else:
                    with pytest.raises(AppError, match="learning material is unavailable"):
                        await fn(db, scope, identifier)


async def test_private_content_export_wipe_preserves_shared_and_other_owner(db, learner, db_path):
    import sqlite3

    from app.db.models import SkillEdge
    from app.db.portability import export_learner, wipe_learner

    db.add(LearnerProfile(id="other", display_name="Other"))
    await db.flush()
    for owner, prefix in [(None, "shared"), (learner.id, "own"), ("other", "foreign")]:
        db.add(
            SkillNode(id=prefix, slug=prefix, domain="ai_ml", title=prefix, owner_learner_id=owner)
        )
    await db.flush()
    for prefix in ["shared", "own", "foreign"]:
        db.add(LearningObject(id=f"{prefix}-object", skill_id=prefix, concept=prefix, goal=prefix))
    await db.flush()
    for prefix in ["shared", "own", "foreign"]:
        db.add(
            Representation(
                id=f"{prefix}-view", object_id=f"{prefix}-object", kind="analogy", content=prefix
            )
        )
    db.add(SkillEdge(id="own-edge", from_skill_id="shared", to_skill_id="own"))
    db.add(SkillEdge(id="foreign-edge", from_skill_id="shared", to_skill_id="foreign"))
    await db.commit()
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        exported = export_learner(conn, learner.id)
        assert [r["id"] for r in exported["skill_node"]] == ["own"]
        assert [r["id"] for r in exported["representation"]] == ["own-view"]
        assert [r["id"] for r in exported["learning_object"]] == ["own-object"]
        wipe_learner(conn, learner.id)
        assert {r[0] for r in conn.execute("SELECT id FROM skill_node")} == {"shared", "foreign"}
        assert {r[0] for r in conn.execute("SELECT id FROM representation")} == {
            "shared-view",
            "foreign-view",
        }
        assert {r[0] for r in conn.execute("SELECT id FROM skill_edge")} == {"foreign-edge"}
        assert not conn.execute("PRAGMA foreign_key_check").fetchall()


def test_ownership_migration_preserves_shared_and_refuses_private_downgrade(tmp_path):
    import sqlite3

    from alembic import command
    from app.db.migrate import alembic_config

    path = tmp_path / "migration.db"
    config = alembic_config(f"sqlite:///{path}")
    command.upgrade(config, "30221b1ed8a7")
    with sqlite3.connect(path) as conn:
        conn.execute(
            "INSERT INTO learner_profile(id, display_name, settings_json, created_at) "
            "VALUES ('a','A','{}','now')"
        )
        conn.execute(
            "INSERT INTO skill_node(id,slug,domain,title,description,success_criteria_json,"
            "assessment_requirements_json,example_applications_json,created_at) "
            "VALUES ('s','s','ai_ml','Shared','','[]','{}','[]','now')"
        )
    command.upgrade(config, "41332c2fe9b8")
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT owner_learner_id FROM skill_node").fetchone()[0] is None
        conn.execute("UPDATE skill_node SET owner_learner_id='a'")
    with pytest.raises(RuntimeError, match="private skills exist"):
        command.downgrade(config, "30221b1ed8a7")
    with sqlite3.connect(path) as conn:
        assert (
            conn.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "41332c2fe9b8"
        )
        conn.execute("UPDATE skill_node SET owner_learner_id=NULL")
    command.downgrade(config, "30221b1ed8a7")
    command.upgrade(config, "41332c2fe9b8")
