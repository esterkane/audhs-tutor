"""Lossless wire formatting; persisted tool results are never edited."""

import json
from typing import Any


def message_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        blocks = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                body = block.get("content")
                if isinstance(body, str) and body.startswith(("{", "[")):
                    try:
                        value = json.loads(body)
                        # Only rewrite the canonical JSON emitted by our tool adapter.
                        # Duplicate keys, custom number spellings and arbitrary text stay exact.
                        canonical = json.dumps(value, ensure_ascii=False, allow_nan=False)
                        if canonical == body:
                            block = {
                                **block,
                                "content": json.dumps(
                                    value,
                                    ensure_ascii=False,
                                    allow_nan=False,
                                    separators=(",", ":"),
                                ),
                            }
                    except (ValueError, RecursionError, OverflowError):
                        pass
            blocks.append(block)
        content = blocks
    return json.dumps(content, ensure_ascii=False, separators=(",", ":"))
