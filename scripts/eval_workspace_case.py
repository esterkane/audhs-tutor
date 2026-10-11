#!/usr/bin/env python3
"""Run one synthetic workspace case locally; semantic acceptance requires manual review."""

import argparse

# ruff: noqa: E402 -- repository-local backend imports require path bootstrap
import asyncio
import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.config import get_settings
from app.evals.harness import open_world
from app.kernel.session import start
from app.orchestrator.playground import VERSION, respond
from app.schemas.common import Mode
from app.schemas.playground import PlaygroundContext, PlaygroundRequest


async def run(case_path: Path, output: Path) -> None:
    if await asyncio.to_thread(case_path.resolve) == await asyncio.to_thread(
        output.resolve
    ):
        raise ValueError("Output must not overwrite the case")
    if urlparse(get_settings().ollama_host).hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise ValueError("Requires loopback Ollama")
    raw = await asyncio.to_thread(case_path.read_bytes)
    case = json.loads(raw)
    if case["intent"] not in {"explain", "hint", "chat"}:
        raise ValueError("This diagnostic excludes grading and execution")
    # Validate before loading a model or creating an evaluation database.
    body = PlaygroundRequest(
        session_id="pending",
        question=case["question"],
        exercise=case["exercise"],
        code="",
        intent=case["intent"],
        questioning_style=case["questioning_style"],
        learning_context=PlaygroundContext(target_id=case["id"]),
    )
    report = {
        "case": case["id"],
        "case_sha256": hashlib.sha256(raw).hexdigest(),
        "synthetic": True,
        "prompt_version": VERSION,
        "scope": "One production respond call, no browser timing or automatic semantic grade",
        "manual_acceptance": case["manual_acceptance"],
        "reference": case["reference"],
        "review_status": "not_reviewed",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="workspace-case-") as directory:
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
                body = body.model_copy(update={"session_id": session.id})
                began = time.perf_counter()
                first = None
                preview = []

                async def token(text: str) -> None:
                    nonlocal first
                    if text.strip() and first is None:
                        first = time.perf_counter() - began
                    preview.append(text)

                try:
                    reply = await asyncio.wait_for(
                        respond(
                            db,
                            world.gateway(db),
                            world.learner_id,
                            body,
                            settings=world.settings,
                            on_token=token,
                        ),
                        timeout=120,
                    )
                    report.update(
                        model=reply.model, text=reply.text, outcome="complete"
                    )
                except Exception as exc:
                    report.update(
                        outcome="error",
                        error_type=type(exc).__name__,
                        preview="".join(preview),
                    )
                    raise
                finally:
                    report.update(
                        first_text_s=first, total_s=time.perf_counter() - began
                    )
                    await asyncio.to_thread(
                        output.write_text, json.dumps(report, indent=2) + "\n"
                    )
        finally:
            await world.close()
    print("Sample recorded; semantic review required.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(run(args.case, args.out))
