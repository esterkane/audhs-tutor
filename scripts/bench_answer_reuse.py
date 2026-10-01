#!/usr/bin/env python3
"""Synthetic buffered-workspace reuse diagnostic on local models and disposable SQLite.

Reports complete-response timing, raw answers and model-call deltas, not token-stream latency
or learning quality. Index population is timed separately. No real learner data is loaded.
"""

import argparse
import asyncio
import json
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from sqlalchemy import func, select
from app.core.config import get_settings
from app.db.models import ModelCall
from app.evals.harness import open_world
from app.kernel.session import start
from app.orchestrator.answer_index import populate
from app.orchestrator.playground import respond
from app.schemas.common import Mode
from app.schemas.playground import PlaygroundContext, PlaygroundRequest


async def run(output: Path) -> None:
    if urlparse(get_settings().ollama_host).hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise ValueError("Diagnostic requires loopback Ollama")
    report = {
        "synthetic": True,
        "scope": "Single paired buffered runs; no streaming or quality gate",
        "runs": [],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="answer-reuse-") as directory:
        world = await open_world(str(Path(directory) / "eval.db"), with_repo=False)
        world.settings = world.settings.model_copy(
            update={
                "openai_api_key": "",
                "anthropic_api_key": "",
                "daily_budget_usd": 0.0,
            }
        )
        try:
            async with world.session_factory() as db:
                session = await start(db, world.learner_id, mode=Mode.STEADY, energy=3)
                gateway = world.gateway(db)
                base = PlaygroundRequest(
                    session_id=session.id,
                    question="Why compare retention rates instead of counts?",
                    exercise="A starts with 100 rows and retains 90; B starts with 50 and retains 30.",
                    code="",
                    learning_context=PlaygroundContext(target_id="synthetic-retention"),
                )
                cases = [
                    ("first", base),
                    ("exact_reuse", base.model_copy(update={"prefer_saved": True})),
                    (
                        "changed_work",
                        base.model_copy(
                            update={
                                "prefer_saved": True,
                                "exercise": "B starts with 50 rows and retains 40. Explain this retention rate.",
                            }
                        ),
                    ),
                    ("fresh_requested", base),
                ]
                for label, body in cases:
                    before = await db.scalar(
                        select(func.count()).select_from(ModelCall)
                    )
                    began = time.perf_counter()
                    reply = await asyncio.wait_for(
                        respond(
                            db, gateway, world.learner_id, body, settings=world.settings
                        ),
                        timeout=120,
                    )
                    elapsed = round((time.perf_counter() - began) * 1000)
                    after = await db.scalar(select(func.count()).select_from(ModelCall))
                    report["runs"].append(
                        {
                            "case": label,
                            "elapsed_ms": elapsed,
                            "model_calls": after - before,
                            "reused": reply.reused,
                            "model": reply.model,
                            "text": reply.text,
                            "saved": reply.answer_id is not None,
                        }
                    )
                    output.write_text(json.dumps(report, indent=2) + "\n")
                    print(label, elapsed, after - before, reply.reused, flush=True)
                    if label == "first":
                        began = time.perf_counter()
                        report["index"] = await populate(
                            db, world.settings, world.learner_id
                        )
                        report["index_ms"] = round((time.perf_counter() - began) * 1000)
        finally:
            await world.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    asyncio.run(run(parser.parse_args().out))
