"""Learner data export and wipe (the only sanctioned way to remove learning_event rows)."""

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.db.ddl import LEARNING_EVENT_GUARDS, drop_guard
from app.db.models import learner_scoped_tables

# These tables have no learner_id but have an attributable owner through a parent.
# Shared corpus and representations with no owned model call are not learner data.
INDIRECT_LEARNER_SCOPES = {
    "representation": (
        "model_call",
        "model_call_id IN (SELECT id FROM model_call WHERE learner_id = ?)",
    ),
    "experiment_arm": (
        "experiment",
        "experiment_id IN (SELECT id FROM experiment WHERE learner_id = ?)",
    ),
}


# Inherited private curriculum content. Ordered children first for wipe.
PRIVATE_CONTENT_SCOPES = {
    "representation": "object_id IN (SELECT id FROM learning_object WHERE skill_id IN "
    "(SELECT id FROM skill_node WHERE owner_learner_id = ?))",
    "learning_object": "skill_id IN (SELECT id FROM skill_node WHERE owner_learner_id = ?)",
    "skill_edge": "to_skill_id IN (SELECT id FROM skill_node WHERE owner_learner_id = ?) "
    "OR from_skill_id IN (SELECT id FROM skill_node WHERE owner_learner_id = ?)",
    "skill_node": "owner_learner_id = ?",
}


def export_learner(conn: sqlite3.Connection, learner_id: str) -> dict[str, list[dict[str, Any]]]:
    conn.row_factory = sqlite3.Row
    out: dict[str, list[dict[str, Any]]] = {}
    for table in learner_scoped_tables():
        rows = conn.execute(
            f'SELECT * FROM "{table}" WHERE learner_id = ?', (learner_id,)
        ).fetchall()
        out[table] = [dict(r) for r in rows]
    for table, (_, predicate) in INDIRECT_LEARNER_SCOPES.items():
        out[table] = [
            dict(row)
            for row in conn.execute(f'SELECT * FROM "{table}" WHERE {predicate}', (learner_id,))
        ]
    out["assessment"] = [
        dict(r)
        for r in conn.execute("SELECT * FROM assessment WHERE owner_learner_id = ?", (learner_id,))
    ]
    out["assessment_rubric"] = [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM assessment_rubric WHERE id IN "
            "(SELECT rubric_id FROM assessment WHERE owner_learner_id = ?)",
            (learner_id,),
        )
    ]
    for table, predicate in PRIVATE_CONTENT_SCOPES.items():
        owned_rows = conn.execute(
            f'SELECT * FROM "{table}" WHERE {predicate}',
            (learner_id,) * predicate.count("?"),
        )
        merged = {r["id"]: r for r in out.get(table, [])}
        merged.update({r["id"]: dict(r) for r in owned_rows})
        out[table] = list(merged.values())
    out["learner_profile"] = [
        dict(r) for r in conn.execute("SELECT * FROM learner_profile WHERE id = ?", (learner_id,))
    ]
    return out


def wipe_learner(conn: sqlite3.Connection, learner_id: str) -> dict[str, int]:
    """Delete every row belonging to the learner. Guard triggers are dropped and recreated
    inside the same transaction so the append-only rule holds for everyone else."""
    deleted: dict[str, int] = {}
    tables = learner_scoped_tables()
    # Cross-table membership guards require dependent links deleted before skill links.
    tables.remove("lesson_activation_skill")
    tables.insert(tables.index("lesson_activation") + 1, "lesson_activation_skill")
    # children before parents: sorted_tables is parent-first, so reverse it
    with conn:
        # sqlite3's implicit transaction starts at DML, not DROP TRIGGER. Start
        # explicitly before guard DDL so a failure restores guards as well as data.
        conn.execute("SAVEPOINT learner_wipe")
        for name in LEARNING_EVENT_GUARDS:
            conn.execute(drop_guard(name))
        for table in reversed(tables):
            # Dependent scoped rows have already gone by topological ordering.
            # Remove indirectly owned children immediately before their parent.
            for child, (parent, predicate) in INDIRECT_LEARNER_SCOPES.items():
                if parent == table:
                    deleted[child] = conn.execute(
                        f'DELETE FROM "{child}" WHERE {predicate}', (learner_id,)
                    ).rowcount
            cur = conn.execute(f'DELETE FROM "{table}" WHERE learner_id = ?', (learner_id,))
            deleted[table] = cur.rowcount
        rubric_ids = [
            r[0]
            for r in conn.execute(
                "SELECT DISTINCT rubric_id FROM assessment WHERE owner_learner_id = ? "
                "AND rubric_id IS NOT NULL",
                (learner_id,),
            )
        ]
        cur = conn.execute("DELETE FROM assessment WHERE owner_learner_id = ?", (learner_id,))
        deleted["assessment"] = cur.rowcount
        deleted["assessment_rubric"] = 0
        for rubric_id in rubric_ids:
            cur = conn.execute(
                "DELETE FROM assessment_rubric WHERE id = ? AND NOT EXISTS "
                "(SELECT 1 FROM assessment WHERE rubric_id = ?)",
                (rubric_id, rubric_id),
            )
            deleted["assessment_rubric"] += cur.rowcount
        for table, predicate in PRIVATE_CONTENT_SCOPES.items():
            count = conn.execute(
                f'DELETE FROM "{table}" WHERE {predicate}',
                (learner_id,) * predicate.count("?"),
            ).rowcount
            deleted[table] = deleted.get(table, 0) + count
        cur = conn.execute("DELETE FROM learner_profile WHERE id = ?", (learner_id,))
        deleted["learner_profile"] = cur.rowcount
        for ddl in LEARNING_EVENT_GUARDS.values():
            conn.execute(ddl)
        conn.execute("RELEASE SAVEPOINT learner_wipe")
    return deleted


def dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


def wipe_voice(voice_dir: Path) -> int:
    """Delete every retained voice recording (P9). Part of a learner wipe; export lists them as
    excluded (audio is not part of the JSON export)."""
    from app.voice.loop import prune

    return prune(voice_dir, 0)
