#!/usr/bin/env python3
"""Populate missing private answer vectors using only an already-installed local model."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.core.config import get_settings
from app.db.session import make_engine, make_session_factory
from app.kernel.learner import get_or_create_owner
from app.orchestrator.answer_index import populate


async def run(limit: int, rebuild: bool) -> None:
    settings = get_settings()
    engine = make_engine(settings.database_url_resolved)
    try:
        async with make_session_factory(engine)() as db:
            owner = await get_or_create_owner(db)
            print(
                json.dumps(
                    await populate(db, settings, owner.id, limit=limit, rebuild=rebuild)
                )
            )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument(
        "--rebuild", action="store_true", help="Recompute selected cached entries"
    )
    args = parser.parse_args()
    asyncio.run(run(args.limit, args.rebuild))
