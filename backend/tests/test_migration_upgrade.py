"""P5 migration-upgrade-test: a database created at a *previous* schema revision and filled with
representative rows must upgrade to head with every row preserved, the data steps applied (vocab
card identity, vocab decks not teachable), new columns present, guards and FK integrity intact.
Disposable databases only."""

import json
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

from alembic import command
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.migrate import alembic_config, upgrade_to_head
from tests._rows import dump_rows, dump_tables, fill_all_tables

FIRST = "08e0e269a737"  # db-core: all phase-1 tables (Stage 0)
STAGE4 = "e2adb21ba4ae"  # stage4 experiments (before the P1/P3/P4 migrations)


@pytest.mark.parametrize("start", [FIRST, STAGE4])
def test_upgrade_from_previous_schema_keeps_data(tmp_path: Path, start: str) -> None:
    db = tmp_path / f"old-{start}.db"
    url = f"sqlite:///{db}"
    command.upgrade(alembic_config(url), start)
    rows = fill_all_tables(url)
    before = dump_rows(url)
    assert "curriculum_draft" not in before  # really an older schema
    upgrade_to_head(url)
    after = dump_rows(url)
    # every old row is preserved *by content* on the columns that existed before (the two tables
    # with intentional data steps are asserted explicitly below); new tables exist and are empty
    for table, recs in before.items():
        assert len(after[table]) == len(recs), table
        if table in ("review_item", "skill_node"):
            continue
        for old, new in zip(recs, after[table], strict=True):
            assert {k: new[k] for k in old} == old, table
    assert after["curriculum_draft"] == [] and after["content_report"] == []
    conn = sqlite3.connect(db)
    # data step P3: the legacy vocab ref gained direction + meaning, schedule row untouched
    prompt = json.loads(
        conn.execute("SELECT prompt_json FROM review_item WHERE item_type='vocab'").fetchone()[0]
    )
    assert prompt["ref"] == "de:forward:haus:house" and prompt["direction"] == "forward"
    assert conn.execute("SELECT count(*) FROM memory_state").fetchone()[0] == 1
    # data step P1: a language deck node is flagged not teachable
    reqs = json.loads(
        conn.execute("SELECT assessment_requirements_json FROM skill_node").fetchone()[0]
    )
    assert reqs.get("teachable") is False and reqs.get("kind") == "vocab_deck"
    # new columns exist with defaults; guards and referential integrity hold
    cols = {r[1] for r in conn.execute("PRAGMA table_info(skill_node)")}
    assert "course" in cols
    assert conn.execute("SELECT course FROM skill_node").fetchone()[0] is None
    triggers = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
    assert {"learning_event_no_update", "learning_event_no_delete"} <= triggers
    conn.execute("PRAGMA foreign_keys=ON")
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    assert conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    conn.close()
    # the upgraded schema equals the ORM's declaration, column for column
    insp = inspect(create_engine(url))
    for name, table in Base.metadata.tables.items():
        assert {c["name"] for c in insp.get_columns(name)} == {c.name for c in table.c}, name
    # the learner row that started it all is still there by id
    assert any(r["id"] == rows["learner_profile"]["id"] for r in after["learner_profile"])


def test_downgrade_one_step_and_back(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'updown.db'}"
    upgrade_to_head(url)
    fill_all_tables(url)
    command.downgrade(alembic_config(url), "-1")
    command.upgrade(alembic_config(url), "head")
    after = dump_tables(url)
    assert len(after["learning_event"]) == 1 and len(after["memory_state"]) == 1
