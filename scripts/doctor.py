#!/usr/bin/env python3
"""Read-only local readiness checks. No app startup, migrations, inference or credential reads."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import Settings  # noqa: E402
from app.core.doctor import diagnose  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["local", "authoring"], default="local")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument(
        "--json", action="store_true", help="Print sanitized machine-readable results"
    )
    args = parser.parse_args()
    if not 0.1 <= args.timeout <= 10:
        parser.error("--timeout must be between 0.1 and 10 seconds")
    try:
        report = asyncio.run(
            diagnose(Settings(), mode=args.mode, api_url=args.api_url, timeout_s=args.timeout)
        )
    except Exception:
        # Settings validation exceptions can contain credential values. Never render exceptions.
        if args.json:
            print(
                json.dumps(
                    {
                        "status": "unavailable",
                        "checks": [
                            {
                                "name": "configuration",
                                "status": "error",
                                "code": "configuration_unavailable",
                                "detail": "Check settings; sensitive values are omitted.",
                            }
                        ],
                    }
                )
            )
        else:
            print(
                "UNAVAILABLE: check application settings; sensitive values are intentionally omitted."
            )
        return 2
    if args.json:
        print(report.model_dump_json(indent=2))
    else:
        print(f"{report.status.upper()} ({report.mode}): read-only checks; no inference or changes")
        for check in report.checks:
            print(f"{check.status.upper():7} {check.name}: {check.detail}")
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
