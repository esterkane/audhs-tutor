#!/usr/bin/env python3
"""Rebuild the Qdrant collection from SQLite. usage: reindex.py [--embedding-version N]"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.db.migrate import upgrade_to_head  # noqa: E402
from app.db.session import make_engine, make_session_factory  # noqa: E402
from app.knowledge.reindex import reindex_all  # noqa: E402


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--embedding-version", type=int, default=1)
    args = ap.parse_args()
    s = get_settings()
    upgrade_to_head(s.sync_database_url)
    engine = make_engine(s.database_url_resolved)
    try:
        async with make_session_factory(engine)() as db:
            collection, n = await reindex_all(db, s, embedding_version=args.embedding_version)
            print(f"reindexed {n} chunks into {collection}")
    finally:
        await engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
