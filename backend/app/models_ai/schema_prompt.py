"""Lossless JSON whitespace compaction, restricted to generated schema instructions."""

import json
from typing import Any

from pydantic import BaseModel

from app.models_ai.provider import Message


def compact_schema_instructions(
    original: list[Message], expanded: list[dict[str, Any]], response_model: type[BaseModel]
) -> list[dict[str, Any]]:
    """Retain every original message and instruction; compact only the appended schema.

    SDK layout changes fail open to the established prompt. Never replace matching
    text in user material, history, or the original system policy.
    """
    if not original or not expanded or original[0].role != "system":
        return expanded
    first = expanded[0]
    content = first.get("content")
    policy = original[0].content
    if (
        first.get("role") != "system"
        or not isinstance(content, str)
        or not content.startswith(policy)
    ):
        return expanded
    schema = response_model.model_json_schema()
    suffix = content[len(policy) :]
    variants = {
        json.dumps(schema, indent=2, ensure_ascii=ascii_only): json.dumps(
            schema, separators=(",", ":"), ensure_ascii=ascii_only
        )
        for ascii_only in (True, False)
    }
    matches = [
        (pretty, compact) for pretty, compact in variants.items() if suffix.count(pretty) == 1
    ]
    if len(matches) != 1:
        return expanded
    pretty, compact = matches[0]
    return [{**first, "content": policy + suffix.replace(pretty, compact)}, *expanded[1:]]
