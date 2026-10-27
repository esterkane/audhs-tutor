#!/usr/bin/env python3
"""Plan or apply backed-up retirement of excluded course sources and the active skill map.

Default is read-only. Receipts and backups must be outside application source directories.
Original files outside the active application are never moved. Historical learner records remain.
"""

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from qdrant_client import models as qm  # noqa: E402
from reset_learning_focus import backup  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.session import make_engine, make_session_factory  # noqa: E402
from app.kernel import content_retirement, focus_reset  # noqa: E402
from app.knowledge.qdrant_transport import local_qdrant_client  # noqa: E402


def write_receipt(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_suffix(".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(value, stream, sort_keys=True)
    temporary.replace(path)


def history(database: Path) -> dict[str, str]:
    result = {}
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as db:
        tables = [
            row[0]
            for row in db.execute(
                "select name from sqlite_master where type='table' and name not like 'sqlite_%'"
            )
        ]
        for table in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            columns = [row[1] for row in db.execute("pragma table_info(" + quoted + ")")]
            if table == "curriculum_draft":
                rows = db.execute(
                    "select * from " + quoted + " where origin='knowledge_authored' order by id"
                ).fetchall()
            elif table == "session":
                keep = [column for column in columns if column != "ended_at"]
                names = ",".join('"' + column + '"' for column in keep)
                rows = db.execute("select " + names + " from " + quoted + " order by id").fetchall()
            elif (
                "learner_id" in columns and table not in {"learner_preference", "review_item"}
            ) or table == "learner_profile":
                rows = db.execute("select * from " + quoted).fetchall()
                rows = sorted(rows, key=repr)
            else:
                continue
            result[table] = hashlib.sha256(
                json.dumps(rows, sort_keys=True, default=str).encode()
            ).hexdigest()
    return result


def asset_paths(root: Path, paths: list[str]) -> list[Path]:
    root = root.resolve()
    result = set()
    for raw in paths:
        parsed = urlparse(raw)
        if parsed.scheme not in {"", "file"}:
            continue
        candidate = Path(unquote(parsed.path if parsed.scheme == "file" else raw))
        if not candidate.is_absolute() or not str(candidate).startswith(str(root) + os.sep):
            continue
        resolved = candidate.resolve()
        if not resolved.is_relative_to(root / "data"):
            continue
        relative = resolved.relative_to(root / "data")
        if relative.parts and relative.parts[0] in {"knowledge-authoring", "models"}:
            continue
        if resolved.suffix.lower() in {".db", ".sqlite", ".sqlite3"} or resolved.name.endswith(
            ("-wal", "-shm")
        ):
            continue
        if resolved.is_file():
            result.add(resolved)
    # Legacy recovered files are retired as a whole, with bytes preserved privately.
    for directory in [
        "transcripts",
        "vision",
        "recovered-originals",
        "online-recovery-downloads",
        "online-current-versions",
        "notebooks",
    ]:
        candidate = root / "data" / directory
        if candidate.is_dir() and candidate.resolve().is_relative_to(root / "data"):
            result.add(candidate.resolve())
    public = root / "frontend/public/local-learning"
    if public.is_dir():
        result.add(public)
    selected = []
    for path in sorted(result, key=lambda value: len(value.parts)):
        if not any(path.is_relative_to(parent) for parent in selected):
            selected.append(path)
    return sorted(selected)


def move_asset(source: Path, root: Path, destination: Path) -> None:
    source = source.resolve()
    root = root.resolve()
    destination = destination.resolve()
    if not source.is_relative_to(root) or destination.is_relative_to(root):
        raise ValueError("Asset boundary validation failed")
    if not source.exists():
        return
    if destination.exists():
        raise ValueError("Backup destination already exists; preserve both copies")
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    shutil.move(str(source), str(destination))


async def remove_indexed_sources(
    url: str, selected: content_retirement.RetirementPlan
) -> dict[str, dict[str, int]]:
    client = local_qdrant_client(url, timeout=120)
    counts = {}
    remaining_counts = {}
    try:
        clauses = []
        if selected.documents:
            clauses.append(
                qm.FieldCondition(key="document_id", match=qm.MatchAny(any=selected.documents))
            )
        if selected.drafts:
            clauses.append(
                qm.FieldCondition(key="source_id", match=qm.MatchAny(any=selected.drafts))
            )
        if not clauses:
            return {"removed": counts, "remaining": remaining_counts}
        criteria = qm.Filter(should=clauses)
        for collection in (await client.get_collections()).collections:
            count = (await client.count(collection.name, count_filter=criteria, exact=True)).count
            if count:
                await client.delete(collection.name, points_selector=criteria, wait=True)
                remaining = (
                    await client.count(collection.name, count_filter=criteria, exact=True)
                ).count
                if remaining:
                    raise RuntimeError("Source points remain after index retirement")
            counts[collection.name] = count
            remaining_counts[collection.name] = (
                await client.count(collection.name, exact=True)
            ).count
        return {"removed": counts, "remaining": remaining_counts}
    finally:
        await client.close()


async def run(args):
    settings = get_settings()
    url = make_url(settings.database_url_resolved)
    if url.get_backend_name() != "sqlite" or not url.database:
        raise ValueError("Saved SQLite database required")
    database = await asyncio.to_thread(Path(url.database).resolve)
    application = await asyncio.to_thread(Path(args.application_root or ROOT).resolve)
    if not await asyncio.to_thread(database.is_file) or not database.is_relative_to(
        application / "data"
    ):
        raise ValueError("Database must exist inside the specified application data directory")
    engine = make_engine(settings.database_url_resolved)
    try:
        async with make_session_factory(engine)() as db:
            selected = await content_retirement.plan(db)
            if not args.apply:
                return {"mode": "plan", **selected.summary()}
            if not args.receipt or not args.backup:
                raise ValueError("Applying requires private --receipt and --backup paths")
            receipt = await asyncio.to_thread(Path(args.receipt).resolve)
            backup_path = await asyncio.to_thread(Path(args.backup).resolve)
            if any(
                path.is_relative_to(root)
                for path in [receipt, backup_path]
                for root in [ROOT, application]
            ):
                raise ValueError(
                    "Backups and receipts must be outside application/source directories"
                )
            if await asyncio.to_thread(receipt.exists):
                state = json.loads(await asyncio.to_thread(receipt.read_text))
                if state["database"] != str(database) or state["application"] != str(application):
                    raise ValueError("Receipt belongs to another application")
                selected = content_retirement.RetirementPlan(**state["plan"])
            else:
                if not args.expected_digest or selected.digest() != args.expected_digest:
                    raise ValueError("Review a fresh dry-run digest before applying")
                await db.rollback()
                await asyncio.to_thread(backup, database, backup_path)
                state = {
                    "database": str(database),
                    "application": str(application),
                    "backup": str(backup_path),
                    "plan": selected.__dict__,
                    "history": await asyncio.to_thread(history, database),
                    "phase": "backed_up",
                    "assets": [
                        str(path)
                        for path in await asyncio.to_thread(
                            asset_paths, application, selected.paths
                        )
                    ],
                }
                await asyncio.to_thread(write_receipt, receipt, state)
            if not await asyncio.to_thread(Path(state["backup"]).is_file):
                raise ValueError("Verified backup file is missing")
            if state["phase"] == "backed_up":
                current = await content_retirement.plan(db)
                if current.digest() != selected.digest():
                    if not await content_retirement.is_redacted(db, selected):
                        raise ValueError(
                            "Source plan changed; inspect the preserved backup before retrying"
                        )
                else:
                    state["index_removed"] = await remove_indexed_sources(
                        settings.qdrant_url, selected
                    )
                    await content_retirement.redact(db, selected)
                    from sqlalchemy import update

                    from app.db.models import IndexState

                    for name, count in state["index_removed"].get("remaining", {}).items():
                        await db.execute(
                            update(IndexState)
                            .where(IndexState.collection == name)
                            .values(chunk_count=count)
                        )
                    await db.commit()
                state["phase"] = "database_redacted"
                await asyncio.to_thread(write_receipt, receipt, state)
            if state["phase"] == "database_redacted":
                for value in state["assets"]:
                    source = Path(value)
                    target = (
                        Path(state["backup"]).parent
                        / "retired-assets"
                        / source.relative_to(application)
                    )
                    await asyncio.to_thread(move_asset, source, application, target)
                state["phase"] = "assets_retired"
                await asyncio.to_thread(write_receipt, receipt, state)
            if state["phase"] == "assets_retired":
                from sqlalchemy import select

                from app.db.models import LearnerProfile

                owners = list(await db.scalars(select(LearnerProfile.id)))
                for owner in owners:
                    await focus_reset.apply(db, owner)
                state["phase"] = "complete"
                await asyncio.to_thread(write_receipt, receipt, state)
            if await asyncio.to_thread(history, database) != state["history"]:
                raise RuntimeError("Historical learner record verification failed")
            return {
                "mode": "applied",
                **selected.summary(),
                "phase": state["phase"],
                "history_preserved": True,
                "map_reset": True,
            }
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--receipt")
    parser.add_argument("--backup")
    parser.add_argument("--expected-digest")
    parser.add_argument("--application-root")
    try:
        print(json.dumps(asyncio.run(run(parser.parse_args())), indent=2))
    except Exception as error:
        parser.exit(2, "Retirement stopped safely: " + type(error).__name__ + "\n")
