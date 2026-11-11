"""Vector-space contracts used by the standalone project's document and query adapters."""

from __future__ import annotations

import math
from collections.abc import Iterable

NOMIC = "nomic-embed-text"
QWEN = "qwen3-embedding:0.6b"
OPENAI = "text-embedding-3-small@768"
QWEN_QUERY = "Instruct: Given a web search query, retrieve relevant passages that answer the query.\nQuery: "
RECORDED_SQL = "select distinct embedding_model from tutor.docs_source where status = 'active'"


def resolve_model(provider: str, configured: str | None, recorded: Iterable[str | None]) -> str:
    """Select the one recorded space, or the provider default for a new corpus."""
    spaces = set(recorded)
    if len(spaces) > 1 or None in spaces:
        raise ValueError(
            "Active documentation has mixed or unidentified embedding models. Rebuild into a separate corpus before switching."
        )
    existing = next(iter(spaces), None)
    model = configured or existing or (NOMIC if provider == "ollama" else OPENAI)
    supported = {"ollama": {NOMIC, QWEN}, "openai": {OPENAI}}
    if model not in supported.get(provider, set()) or (existing and existing != model):
        raise ValueError(
            "Embedding selection is incompatible with the documentation corpus. Use its recorded provider/model or rebuild separately."
        )
    return model


def ollama_input(text: str, model: str, *, query: bool) -> str:
    if model == QWEN:
        return (QWEN_QUERY if query else "") + text
    if model == NOMIC:
        return ("search_query: " if query else "search_document: ") + text
    raise ValueError("Unsupported local documentation embedding model.")


def ollama_payload(texts: list[str], model: str, *, query: bool) -> dict[str, object]:
    payload: dict[str, object] = {
        "model": model,
        "input": [ollama_input(text, model, query=query) for text in texts],
    }
    if model == QWEN:
        payload["truncate"] = False
        payload["dimensions"] = 768
    return payload


def checked_vectors(vectors: list[list[float]], count: int) -> list[list[float]]:
    if (
        not isinstance(vectors, list)
        or len(vectors) != count
        or any(
            not isinstance(vector, list)
            or len(vector) != 768
            or not all(
                isinstance(v, (float, int)) and not isinstance(v, bool) and math.isfinite(v) for v in vector
            )
            for vector in vectors
        )
    ):
        raise ValueError(
            "Documentation embedding response must contain one finite 768-dimensional vector per input."
        )
    return vectors
