#!/usr/bin/env python3
"""Local semantic-answer retrieval diagnostic with synthetic hard negatives, no generation."""

import argparse
import asyncio
import json
import math
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import get_settings
from app.db.traces import ModelCallRecord, write_model_call
from app.evals.harness import open_world
from app.knowledge.reindex import embed_spec
from app.models_ai.ollama import OllamaProvider

DOCUMENTS = [
    (
        "retention",
        "Why compare retention rates? Divide retained rows by initial group size to compare proportions.",
    ),
    (
        "incorrect",
        "Why compare retention rates? Divide initial group size by retained rows to compare proportions.",
    ),
    (
        "missing",
        "How can missing data bias cleaning? Dropping rows may remove more members of some groups.",
    ),
    (
        "syntax",
        "How do I access the second list item in Python? Use values[1]; indexing starts at zero.",
    ),
    (
        "bins",
        "Which bin contains the boundary? Specify whether each interval includes its left or right endpoint.",
    ),
    ("unrelated", "How do I tune a guitar? Standard strings are E A D G B E."),
]
QUERIES = [
    (
        "How do I compare the fraction remaining when groups started at different sizes?",
        "retention",
    ),
    ("Could removing incomplete records distort who is represented?", "missing"),
    ("Retrieve element number two from a Python sequence", "syntax"),
    ("Where does a value exactly on a bucket edge belong?", "bins"),
]


def cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a or not all(math.isfinite(x) for x in a + b):
        raise ValueError("Invalid embedding vector")
    denominator = math.sqrt(sum(x * x for x in a) * sum(x * x for x in b))
    return (
        sum(x * y for x, y in zip(a, b, strict=True)) / denominator
        if denominator
        else 0.0
    )


async def run(output: Path) -> None:
    if urlparse(get_settings().ollama_host).hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise ValueError("Loopback Ollama required")
    with tempfile.TemporaryDirectory(prefix="audhs-semantic-eval-") as temporary:
        world = await open_world(str(Path(temporary) / "eval.db"), with_repo=False)
        try:
            async with world.session_factory() as db:
                spec = await embed_spec(db, world.settings)
                if spec.provider != "ollama":
                    raise ValueError("Only installed local Ollama embeddings allowed")
                provider = OllamaProvider(world.settings.ollama_host)
                timings = []

                async def embed(texts: list[str]) -> list[list[float]]:
                    started = time.perf_counter()
                    ok = False
                    try:
                        vectors = await provider.embed(spec, texts)
                        ok = True
                        return vectors
                    finally:
                        elapsed = round((time.perf_counter() - started) * 1000)
                        timings.append(elapsed)
                        await write_model_call(
                            db,
                            ModelCallRecord(
                                provider=spec.provider,
                                model=spec.model,
                                registry_id=spec.registry_id,
                                task="embed",
                                learner_id=world.learner_id,
                                latency_ms=elapsed,
                                ok=ok,
                                outcome="ok" if ok else "error",
                                metadata={
                                    "task": "answer_search_eval",
                                    "batch_size": len(texts),
                                },
                            ),
                        )

                document_vectors = await embed([text for _, text in DOCUMENTS])
                results = []
                for query, expected in QUERIES:
                    vector = (await embed([query]))[0]
                    ranking = sorted(
                        [
                            {"id": identifier, "score": cosine(vector, candidate)}
                            for (identifier, _), candidate in zip(
                                DOCUMENTS, document_vectors, strict=True
                            )
                        ],
                        key=lambda row: row["score"],
                        reverse=True,
                    )
                    results.append(
                        {"query": query, "expected": expected, "ranking": ranking}
                    )
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(
                    json.dumps(
                        {
                            "model": spec.registry_id,
                            "synthetic": True,
                            "scope": "unprefixed embedding cosine only, no production integration or truth validation",
                            "document_batch_ms": timings[0],
                            "query_ms": timings[1:],
                            "documents": DOCUMENTS,
                            "results": results,
                        },
                        indent=2,
                    )
                )
                print(
                    json.dumps(
                        {
                            "model": spec.registry_id,
                            "query_ms": timings[1:],
                            "top1": [row["ranking"][0]["id"] for row in results],
                        }
                    )
                )
        finally:
            await world.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    asyncio.run(run(parser.parse_args().out))
