"""Reuse a green predecessor only for Markdown-only main pushes; uncertainty runs all gates."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path


def markdown_only(paths: list[str]) -> bool:
    return bool(paths) and all(
        path == "README.md" or (path.startswith("docs/") and path.endswith(".md")) for path in paths
    )


def green_predecessor(runs: object, before: str) -> bool:
    return (
        isinstance(runs, list)
        and bool(runs)
        and all(
            isinstance(run, dict)
            and run.get("headSha") == before
            and run.get("status") == "completed"
            and run.get("conclusion") == "success"
            for run in runs
        )
    )


def command(args: list[str]) -> str:
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=45).stdout


def needs_runtime() -> bool:
    if os.environ.get("GITHUB_EVENT_NAME") != "push":
        return True
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    before, head = event.get("before", ""), os.environ.get("GITHUB_SHA", "")
    if not all(re.fullmatch(r"[0-9a-f]{40}", sha) and sha != "0" * 40 for sha in (before, head)):
        return True
    # Exact push base may be outside checkout's shallow history. Never substitute HEAD~1.
    command(["git", "fetch", "--no-tags", "--depth=1", "origin", before])
    changed = command(["git", "diff", "--no-renames", "--name-only", "-z", before, head])
    paths = changed.rstrip("\0").split("\0") if changed else []
    if not markdown_only(paths):
        return True
    runs = json.loads(
        command(
            [
                "gh",
                "run",
                "list",
                "--repo",
                os.environ["GITHUB_REPOSITORY"],
                "--workflow",
                "ci.yml",
                "--commit",
                before,
                "--event",
                "push",
                "--limit",
                "1",
                "--json",
                "headSha,status,conclusion",
            ]
        )
    )
    return not green_predecessor(runs, before)


def main() -> None:
    try:
        full = needs_runtime()
    except (OSError, ValueError, KeyError, TypeError, AttributeError, subprocess.SubprocessError):
        full = True
    print(f"runtime={'true' if full else 'false'}")
    print(
        "Run all runtime gates." if full else "Markdown-only change; predecessor CI passed.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
