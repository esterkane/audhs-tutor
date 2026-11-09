"""Lossless wire formatting; persisted tool results are never edited."""

import json
from collections import Counter
from typing import Any

# Character count, not bytes: skip parsing larger historical bodies entirely.
MAX_TOOL_RESULT_CHARS = 256 * 1024


def _search_envelope(value: Any) -> bool:
    if not isinstance(value, dict) or not isinstance(value.get("results"), list):
        return False
    if not value.keys() <= {"results", "note", "scope_note"}:
        return False
    for hit in value["results"]:
        if not isinstance(hit, dict):
            return False
        if not all(
            isinstance(hit.get(key), str) for key in ("url", "title", "heading_path", "content")
        ):
            return False
        if type(hit.get("tier")) is not int or type(hit.get("score")) not in (int, float):
            return False
        if "fetched_at" not in hit or (
            hit["fetched_at"] is not None and not isinstance(hit["fetched_at"], str)
        ):
            return False
    return True


def _compact_search_result(block: dict[str, Any]) -> dict[str, Any]:
    body = block.get("content")
    if not isinstance(body, str) or len(body) > MAX_TOOL_RESULT_CHARS or not body.startswith("{"):
        return block
    try:
        value = json.loads(body)
        if not _search_envelope(value):
            return block
        # Only canonical JSON emitted by the tool adapter: no duplicate keys,
        # custom number spellings, nonfinite numbers or arbitrary text.
        if json.dumps(value, ensure_ascii=False, allow_nan=False) != body:
            return block
        return {
            **block,
            "content": json.dumps(
                value,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            ),
        }
    except (ValueError, RecursionError, OverflowError):
        return block


def message_content(content: Any) -> str:
    """Without verified request provenance, only format the outer message."""
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False, separators=(",", ":"))


def message_contents(messages: list[dict[str, Any]]) -> list[str]:
    """Compact only unique, preceding search_docs calls' successful user results.

    Count IDs across the whole request, including malformed-role occurrences, so a
    repeated ID cannot become eligible merely because its other use appears later.
    The original messages remain available unchanged for guards and persistence.
    """
    calls: dict[str, tuple[int, str, Any]] = {}
    call_counts: Counter[str] = Counter()
    result_counts: Counter[str] = Counter()
    for index, message in enumerate(messages):
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                identity = block.get("id")
                if isinstance(identity, str) and identity:
                    call_counts[identity] += 1
                    calls[identity] = (index, message.get("role", ""), block.get("name"))
            elif block.get("type") == "tool_result":
                identity = block.get("tool_use_id")
                if isinstance(identity, str) and identity:
                    result_counts[identity] += 1

    output = []
    for index, message in enumerate(messages):
        content = message.get("content", "")
        if message.get("role") == "user" and isinstance(content, list):
            blocks = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    identity = block.get("tool_use_id")
                    if isinstance(identity, str):
                        call = calls.get(identity)
                        if (
                            call is not None
                            and call[0] < index
                            and call[1:] == ("assistant", "search_docs")
                            and call_counts[identity] == result_counts[identity] == 1
                            and block.get("is_error") is False
                        ):
                            block = _compact_search_result(block)
                blocks.append(block)
            content = blocks
        output.append(message_content(content))
    return output
