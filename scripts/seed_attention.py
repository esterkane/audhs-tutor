#!/usr/bin/env python3
"""Seed the attention curriculum (skills, learning objects, assessments, sources) and reindex Qdrant.
usage: seed_attention.py [--no-index]"""

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.db.migrate import upgrade_to_head  # noqa: E402
from app.db.session import make_engine, make_session_factory  # noqa: E402
from app.kernel.seed import load_seed  # noqa: E402
from app.knowledge.reindex import reindex_all  # noqa: E402


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-index", action="store_true")
    ap.add_argument("--seed", default="attention")
    args = ap.parse_args()
    s = get_settings()
    upgrade_to_head(s.sync_database_url)
    engine = make_engine(s.database_url_resolved)
    try:
        async with make_session_factory(engine)() as db:
            rep = await load_seed(db, ROOT / "seeds" / args.seed)
            print(
                f"skills={rep.skills} edges={rep.edges} learning_objects={rep.learning_objects} "
                f"assessments={rep.assessments}"
            )
            for d in rep.documents:
                print(
                    f"  {d['file']}: v{d['version']} {d['chunks']} chunks {'(new)' if d['changed'] else '(unchanged)'}"
                )
            if not args.no_index:
                collection, n = await reindex_all(db, s)
                print(f"reindexed {n} chunks into {collection}")
    finally:
        await engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
