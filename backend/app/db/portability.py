"""Learner data export and wipe (the only sanctioned way to remove learning_event rows)."""

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.db.ddl import LEARNING_EVENT_GUARDS, drop_guard
from app.db.models import learner_scoped_tables


def export_learner(conn: sqlite3.Connection, learner_id: str) -> dict[str, list[dict[str, Any]]]:
    conn.row_factory = sqlite3.Row
    out: dict[str, list[dict[str, Any]]] = {}
    for table in learner_scoped_tables():
        rows = conn.execute(
            f'SELECT * FROM "{table}" WHERE learner_id = ?', (learner_id,)
        ).fetchall()
        out[table] = [dict(r) for r in rows]
    out["learner_profile"] = [
        dict(r) for r in conn.execute("SELECT * FROM learner_profile WHERE id = ?", (learner_id,))
    ]
    return out


def wipe_learner(conn: sqlite3.Connection, learner_id: str) -> dict[str, int]:
    """Delete every row belonging to the learner. Guard triggers are dropped and recreated
    inside the same transaction so the append-only rule holds for everyone else."""
    deleted: dict[str, int] = {}
    tables = learner_scoped_tables()
    # children before parents: sorted_tables is parent-first, so reverse it
    with conn:
        for name in LEARNING_EVENT_GUARDS:
            conn.execute(drop_guard(name))
        for table in reversed(tables):
            cur = conn.execute(f'DELETE FROM "{table}" WHERE learner_id = ?', (learner_id,))
            deleted[table] = cur.rowcount
        cur = conn.execute("DELETE FROM learner_profile WHERE id = ?", (learner_id,))
        deleted["learner_profile"] = cur.rowcount
        for ddl in LEARNING_EVENT_GUARDS.values():
            conn.execute(ddl)
    return deleted


def dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


def wipe_voice(voice_dir: Path) -> int:
    """Delete every retained voice recording (P9). Part of a learner wipe; export lists them as
    excluded (audio is not part of the JSON export)."""
    from app.voice.loop import prune

    return prune(voice_dir, 0)
