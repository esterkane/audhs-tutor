#!/usr/bin/env python3
"""Export all data for one learner as JSON.  usage: export.py --learner <id> [--out file.json]"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.db.portability import dumps, export_learner  # noqa: E402
from app.db.session import sync_connect  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--learner", required=True)
    ap.add_argument("--out")
    args = ap.parse_args()
    conn = sync_connect(get_settings().sync_database_url)
    payload = dumps(export_learner(conn, args.learner))
    if args.out:
        Path(args.out).write_text(payload)
        print(f"wrote {args.out}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
