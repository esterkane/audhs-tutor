"""Optional local token counting for capacity reservation, never content truncation.

The configured tokenizer must match the installed model. Count message content
exactly and reserve generous chat-template overhead plus the entire output ceiling.
Unknown models and unusable assets keep their original capacity. Structured callers
first expand the exact Instructor schema messages before counting.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any

import litellm

from app.models_ai.provider import Message


@lru_cache(maxsize=8)
def _load(path: str, mtime_ns: int, size: int) -> Any:
    tokenizer = litellm.create_tokenizer(Path(path).read_text())["tokenizer"]
    tokenizer.no_truncation()
    tokenizer.no_padding()
    return tokenizer


def context_capacity(
    ceiling: int,
    messages: list[Message],
    max_tokens: int,
    tokenizer_path: str | None,
) -> int:
    if not tokenizer_path or ceiling <= 8192:
        return ceiling
    try:
        path = Path(tokenizer_path)
        stat = path.stat()
        tokenizer = _load(str(path), stat.st_mtime_ns, stat.st_size)
        content = sum(
            len(tokenizer.encode(m.content, add_special_tokens=False).ids) for m in messages
        )
    except Exception:
        return ceiling
    # Text chat: role/delimiter overhead is normally a few tokens.
    # Keep 256 per message plus 512 tail tokens; never reduce the output ceiling.
    required = content + 256 * len(messages) + 512 + max_tokens
    capacity = 8192
    while capacity < required:
        capacity *= 2
    return min(capacity, ceiling)
