#!/usr/bin/env python3
"""Synthetic local mode-compliance samples; manual review, not an automatic quality grade."""

import argparse
import hashlib
import asyncio
import json
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.core.config import get_settings
from app.evals.harness import open_world
from app.models_ai.provider import TaskClass
from app.orchestrator.playground import VERSION, messages
from app.schemas.playground import PlaygroundMessage, PlaygroundRequest

CASES = [
    (
        "socratic_start",
        "chat",
        "Help me reason about this rate, one question at a time.",
        [],
        "Give enough context and one focused question, not the complete calculation.",
    ),
    (
        "socratic_feedback",
        "chat",
        "My answer is 90%. Give feedback on my reasoning first.",
        [
            PlaygroundMessage(
                role="assistant",
                text="What fraction of the original 50 rows are the remaining 30?",
            ),
            PlaygroundMessage(role="user", text="30/50 = 0.9, so 90%."),
        ],
        "Correct the specific arithmetic before any optional single follow-up; no mastery claim.",
    ),
    (
        "socratic_hint",
        "hint",
        "Give one small clue for your last question; do not solve it.",
        [
            PlaygroundMessage(
                role="assistant", text="Which count belongs in the denominator?"
            )
        ],
        "Hint about the original count, no replacement question or complete answer.",
    ),
]


async def run(output: Path) -> None:
    if urlparse(get_settings().ollama_host).hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise ValueError("Local evaluation only")
    results = []
    with tempfile.TemporaryDirectory(prefix="workspace-modes-") as directory:
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
                gateway = world.gateway(db)
                for name, intent, question, history, review in CASES:
                    body = PlaygroundRequest(
                        session_id="eval",
                        exercise="A dataset starts with 50 rows and retains 30.",
                        code="",
                        question=question,
                        history=history,
                        intent=intent,
                        questioning_style="socratic",
                    )
                    reply = await asyncio.wait_for(
                        gateway.complete(
                            TaskClass.HINT
                            if intent == "hint"
                            else TaskClass.EXPLAIN_SIMPLE,
                            messages(body),
                            learner_id=world.learner_id,
                            max_tokens=400,
                            metadata={
                                "task": "workspace_mode_eval",
                                "prompt_version": VERSION,
                                "task_prompt_sha256": hashlib.sha256(
                                    (
                                        Path(__file__).resolve().parents[1]
                                        / "prompts/playground/tutor.v2.md"
                                    ).read_bytes()
                                ).hexdigest(),
                            },
                        ),
                        timeout=120,
                    )
                    results.append(
                        {
                            "case": name,
                            "review_criteria": review,
                            "text": reply.result.text,
                            "model": reply.registry_id,
                        }
                    )
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_text(
                        json.dumps(
                            {
                                "synthetic": True,
                                "prompt_version": VERSION,
                                "task_prompt_sha256": hashlib.sha256(
                                    (
                                        Path(__file__).resolve().parents[1]
                                        / "prompts/playground/tutor.v2.md"
                                    ).read_bytes()
                                ).hexdigest(),
                                "results": results,
                            },
                            indent=2,
                        )
                        + "\n"
                    )
                    print(name, "completed", flush=True)
        finally:
            await world.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    asyncio.run(run(parser.parse_args().out))
