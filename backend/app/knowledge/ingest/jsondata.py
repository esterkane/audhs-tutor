"""Conservative JSON record datasets; preserve values and never execute content."""

import json
from typing import Any

from app.knowledge.ingest.types import Block


def dataset_blocks(value: Any) -> list[Block] | None:
    """Recognize records or named record collections, not arbitrary configuration."""
    # Nested workflow exports must not bypass the dedicated allowlist parser.
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            if "nodes" in item and "connections" in item:
                return None
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    groups = {"Records": value} if isinstance(value, list) else value
    if not isinstance(groups, dict) or not groups:
        return None
    if not all(
        isinstance(rows, list) and rows and all(isinstance(row, dict) and row for row in rows)
        for rows in groups.values()
    ):
        return None
    return [
        Block(
            text=json.dumps(row, ensure_ascii=False, indent=2),
            kind="code",
            heading=f"JSON dataset · {name} · record {index}",
        )
        for name, rows in groups.items()
        for index, row in enumerate(rows, 1)
    ]
