"""Test helper: fill every table of a (possibly older-schema) SQLite database with one
representative row each, by *reflection* — so it works at any Alembic revision. Returns the
inserted rows per table so tests can compare them after a migration or a restore."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import JSON, Boolean, Float, Integer, MetaData, Table, create_engine, insert, text
from sqlalchemy.engine import Engine

from app.db.ddl import LEARNING_EVENT_GUARDS, drop_guard

_ULID = "01J{:023d}"
# JSON columns whose ORM default is a list (everything else is a dict)
LIST_JSON_COLUMNS = frozenset(
    {
        "chunk_ids_json",
        "skill_ids_json",
        "flags_json",
        "flagged_patterns_json",
        "criteria_json",
        "sources_json",
        "examples_json",
        "exercises_json",
        "success_criteria_json",
        "example_applications_json",
        "dropped_json",
        "validation_json",
        "plan_json",
        "cited_sources_json",
    }
)


def _value(table: Table, col: Any, n: int, ids: dict[str, str]) -> Any:
    if col.foreign_keys:
        fk = next(iter(col.foreign_keys))
        parent = fk.column.table.name
        if parent == table.name:  # self reference (chunk.duplicate_of)
            return None
        return ids[parent]
    if col.primary_key:
        return _ULID.format(n) if not table.name == "model_registry" else f"model-{n}"
    name = col.name
    t = col.type
    if isinstance(t, JSON):
        return (
            []
            if name.endswith(("_ids_json", "s_json", "criteria_json", "sources_json"))
            or name
            in (
                "examples_json",
                "exercises_json",
                "success_criteria_json",
                "example_applications_json",
                "bm25_scores_json",
                "vector_scores_json",
                "fused_json",
                "reranked_json",
            )
            else {"k": f"{table.name}-{n}"}
        )
    if isinstance(t, Boolean):
        return True
    if isinstance(t, Integer):
        return 1
    if isinstance(t, Float):
        return 0.5
    # text-ish: give a few well-known columns plausible values so data migrations run over them
    if name == "domain":
        return "ai_ml"
    if name == "status":
        return (
            "ready"
            if table.name == "model_registry"
            else "draft"
            if table.name == "curriculum_draft"
            else "open"
        )
    if name == "item_type":
        return "vocab"
    if name == "verb":
        return "started"
    if name == "kind":
        return (
            "prerequisite"
            if table.name == "skill_edge"
            else "mcq"
            if table.name == "assessment"
            else "wrong_source"
        )
    if name in (
        "due",
        "ts",
        "created_at",
        "expires_at",
        "started_at",
        "ingested_at",
        "added_at",
        "last_review",
    ):
        return "2026-09-20T10:00:00+00:00"
    if name == "slug":
        return f"{table.name}-{n}"
    if name in ("mode",):
        return "steady"
    if name == "unit_type":
        return "node"
    return f"{table.name}.{name}.{n}"


def fill_all_tables(sync_url: str, *, seq: int = 1) -> dict[str, dict[str, Any]]:
    """One row per table (parents first). `seq` varies the ids so a DB can be filled twice."""
    engine: Engine = create_engine(sync_url)
    meta = MetaData()
    meta.reflect(bind=engine)
    rows: dict[str, dict[str, Any]] = {}
    ids: dict[str, str] = {}
    with engine.begin() as conn:
        for guard in LEARNING_EVENT_GUARDS:
            conn.execute(
                text(drop_guard(guard))
            )  # append-only triggers block nothing here (insert) but keep symmetric
        for n, table in enumerate(meta.sorted_tables, start=seq * 1000):
            if table.name == "alembic_version":
                continue
            row = {c.name: _value(table, c, n, ids) for c in table.columns}
            if table.name == "review_item":  # legacy vocab card, the P3 data migration rewrites it
                row["prompt_json"] = {"ref": "de:Haus", "q": "Haus", "a": "house", "lang": "de"}
            if table.name == "skill_node":
                row["slug"] = f"lang-deck-{n}"
                row["domain"] = "language"
            conn.execute(insert(table).values(**row))
            pk = [c.name for c in table.primary_key.columns][0]
            ids[table.name] = str(row[pk])
            rows[table.name] = row
        for ddl in LEARNING_EVENT_GUARDS.values():
            conn.execute(text(ddl))
    engine.dispose()
    return rows


def dump_tables(sync_url: str) -> dict[str, list[tuple[Any, ...]]]:
    """Every table's rows (sorted), JSON columns normalised, for equality checks."""
    return {
        t: sorted(
            tuple(json.dumps(r[c], sort_keys=True, default=str) for c in sorted(r)) for r in rows
        )
        for t, rows in dump_rows(sync_url).items()
    }


def dump_rows(sync_url: str) -> dict[str, list[dict[str, Any]]]:
    """Every table's rows as dicts (JSON columns decoded), sorted by primary key."""
    engine = create_engine(sync_url)
    meta = MetaData()
    meta.reflect(bind=engine)
    out: dict[str, list[dict[str, Any]]] = {}
    with engine.connect() as conn:
        for table in meta.sorted_tables:
            if table.name == "alembic_version":
                continue
            recs = conn.execute(table.select()).mappings().all()
            rows = []
            for r in recs:
                row: dict[str, Any] = {}
                for c in table.columns:
                    v = r[c.name]
                    if isinstance(v, str) and isinstance(c.type, JSON):
                        v = json.loads(v)
                    row[c.name] = v
                rows.append(row)
            out[table.name] = sorted(rows, key=lambda d: str(d.get("id", "")))
    engine.dispose()
    return out
