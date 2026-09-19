#!/usr/bin/env python3
"""Delete all data for one learner.  usage: wipe.py --learner <id> --yes"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.db.portability import wipe_learner  # noqa: E402
from app.db.session import sync_connect  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--learner", required=True)
    ap.add_argument("--yes", action="store_true", help="required; there is no undo")
    args = ap.parse_args()
    if not args.yes:
        print("refusing without --yes (export first with scripts/export.py)", file=sys.stderr)
        return 2
    conn = sync_connect(get_settings().sync_database_url)
    for table, n in wipe_learner(conn, args.learner).items():
        if n:
            print(f"{table}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
