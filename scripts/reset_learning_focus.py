#!/usr/bin/env python3
"""Plan a focused map reset; applying requires a new private SQLite backup outside the repository.

No course files are purged by this command. Historical session/answer rows remain intact.
"""

import argparse
import asyncio
import json
import os
import sqlite3
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.config import get_settings  # noqa: E402
from app.db.models import LearnerProfile  # noqa: E402
from app.db.session import make_engine, make_session_factory  # noqa: E402
from app.kernel import focus_reset  # noqa: E402


def backup(source: Path, target: Path) -> None:
    target = target.resolve()
    if target.is_relative_to(ROOT) or target.exists() or target == source.resolve():
        raise ValueError("Use a new private backup file outside the repository")
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    try:
        with sqlite3.connect(f"file:{source.resolve()}?mode=ro", uri=True) as original:
            with sqlite3.connect(target) as copy:
                original.backup(copy)
                if copy.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("Backup integrity check failed")
    except BaseException:
        target.unlink(missing_ok=True)
        raise


async def run(args: argparse.Namespace) -> dict:
    settings = get_settings()
    url = make_url(settings.database_url_resolved)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        raise ValueError("This reset command requires a saved local SQLite database")
    database = await asyncio.to_thread(Path(url.database).resolve)
    if not await asyncio.to_thread(database.is_file):
        raise ValueError("Existing database required; no empty database will be created")
    engine = make_engine(settings.database_url_resolved)
    try:
        async with make_session_factory(engine)() as db:
            owners = list(await db.scalars(select(LearnerProfile.id)))
            owner = args.learner_id or (owners[0] if len(owners) == 1 else None)
            if owner not in owners:
                raise ValueError(
                    "Select an existing learner explicitly when there are multiple profiles"
                )
            before = await focus_reset.plan(db, owner)
            if not args.apply:
                return {"mode": "plan", **before}
            if not args.backup:
                raise ValueError("Applying requires --backup pointing to a new private backup file")
            # End the read transaction before taking a consistent SQLite backup and applying.
            await db.rollback()
            await asyncio.to_thread(backup, database, Path(args.backup))
            cutoff = await focus_reset.apply(db, owner)
            return {
                "mode": "applied",
                "reference_before": cutoff,
                "backup_verified": True,
                "history_preserved": True,
                "purges_course_files": False,
            }
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup")
    parser.add_argument("--learner-id")
    try:
        print(json.dumps(asyncio.run(run(parser.parse_args())), indent=2))
    except (ValueError, OSError) as error:
        parser.exit(2, str(error) + "\n")
