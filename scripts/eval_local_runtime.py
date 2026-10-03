#!/usr/bin/env python3
"""Synthetic actual-workspace diagnostic; local only, no automatic semantic pass claim."""

import argparse
import asyncio
import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import get_settings
from app.db.models import ModelCall, TutorAnswer
from app.evals.harness import open_world
from app.kernel import session as sessions
from app.models_ai.benchmark_gateway import BenchmarkRouter
from app.models_ai.registry import get_row, get_spec
from app.orchestrator import playground
from app.schemas.common import Mode
from app.schemas.playground import PlaygroundContext, PlaygroundRequest
from sqlalchemy import select


def local_settings(settings):
    if urlparse(settings.ollama_host).hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Loopback Ollama required")
    return settings.model_copy(
        update={"openai_api_key": "", "anthropic_api_key": "", "daily_budget_usd": 0.0}
    )


async def pinned_gateway(world, db, model):
    world.settings = local_settings(world.settings)
    row, spec = await get_row(db, model), await get_spec(db, model)
    if row.status != "ready" or spec.provider != "ollama" or spec.hosted:
        raise ValueError("Installed local Ollama candidate required")
    gateway = world.gateway(db)
    gateway.router = BenchmarkRouter(model)
    if set(gateway.providers) != {"ollama"}:
        raise ValueError("Diagnostic must construct only the local provider")
    return gateway


class RecordedGateway:
    def __init__(self, gateway):
        self.gateway = gateway
        self.requests = []

    async def complete(self, task, messages, **kwargs):
        packet = [message.model_dump() for message in messages]
        record = {
            "task": str(task),
            "messages": packet,
            "messages_sha256": hashlib.sha256(
                json.dumps(packet, sort_keys=True, ensure_ascii=False).encode()
            ).hexdigest(),
            "max_tokens": kwargs.get("max_tokens"),
            "structured_schema_requested": kwargs.get("response_model") is not None,
        }
        self.requests.append(record)
        result = await self.gateway.complete(task, messages, **kwargs)
        record["raw_final_model_text"] = result.result.text
        return result


def cases(session_id):
    base = PlaygroundRequest(
        session_id=session_id,
        intent="check_answer",
        question="Review my reasoning against the supplied task.",
        exercise="A group starts with 50 rows and retains 30. What proportion remains?",
        learner_answer="30/50 = 0.9, so 90%.",
        code="",
        learning_context=PlaygroundContext(target_id="synthetic-retention"),
    )
    return [
        (
            "wrong_answer",
            base,
            "Correct to 60%; no invented execution or official grade.",
        ),
        (
            "exact_reuse",
            base.model_copy(update={"prefer_saved": True}),
            "Reopen the identical eligible response with zero gateway requests; no new check.",
        ),
        (
            "changed_answer",
            base.model_copy(
                update={"prefer_saved": True, "learner_answer": "30/50 = 0.6, or 60%."}
            ),
            "Do not replay prior feedback; accept this correction.",
        ),
        (
            "unrun_python",
            PlaygroundRequest(
                session_id=session_id,
                intent="check_answer",
                question="Check my explanation of this Python code.",
                exercise="Explain values[1] for values = [10, 20, 30]. No execution was supplied.",
                learner_answer="It should select 20, because indexing starts at zero. I have not run it.",
                code="values = [10, 20, 30]\nprint(values[1])",
                learning_context=PlaygroundContext(target_id="synthetic-python"),
            ),
            "Accept indexing explanation without claiming code execution.",
        ),
    ]


async def evaluate_case(
    db, gateway, learner_id, name, body, criteria, settings, on_respond=None
):
    before = set(await db.scalars(select(ModelCall.id)))
    recorder = RecordedGateway(gateway)
    result = {
        "case": name,
        "request": body.model_dump(exclude={"session_id"}),
        "manual_review_criteria": criteria,
        "semantic_review": "not_reviewed",
        "gateway_requests": recorder.requests,
    }
    started = time.perf_counter()
    try:
        if on_respond is not None:
            on_respond()
        reply = await asyncio.wait_for(
            playground.respond(db, recorder, learner_id, body, settings=settings),
            timeout=120,
        )
        result["reply"] = reply.model_dump()
        result["status"] = "completed"
        saved = await db.get(TutorAnswer, reply.answer_id) if reply.answer_id else None
        result["saved_metadata"] = saved.metadata_json if saved else None
        result["literal_schema_validated_this_run"] = (
            body.intent == "check_answer" and not reply.reused
        )
    except Exception as exc:  # noqa: BLE001 — retain each failure without hiding later cases
        await db.rollback()
        result.update(status="failed", error_type=type(exc).__name__)
        result["literal_schema_validated_this_run"] = None
    result["elapsed_ms"] = round((time.perf_counter() - started) * 1000)
    calls = list(await db.scalars(select(ModelCall).where(ModelCall.id.not_in(before))))
    result["attempts"] = [
        {
            key: getattr(call, key)
            for key in (
                "registry_id",
                "model",
                "provider",
                "task",
                "request_id",
                "attempt",
                "outcome",
                "latency_ms",
                "tokens_in",
                "tokens_out",
                "cost_usd",
            )
        }
        for call in calls
    ]
    return result


async def run(output, model):
    local_settings(get_settings())  # reject remote host before harness discovery
    report = {
        "report_version": 1,
        "synthetic": True,
        "pinned_feedback_generation_model": model,
        "ancillary_models": "local embedding lookup may use a different local model",
        "runtime_respond_exercised": False,
        "production_routing_exercised": False,
        "fallback_allowed": False,
        "runtime_prompt_version": playground.VERSION,
        "scope": "four ordered synthetic runtime cases, not a quality or latency benchmark",
        "results": [],
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    # Reserve before setup; never truncate an existing artifact or follow an existing symlink.
    artifact = output.open("x")

    def persist(status):
        report["status"] = status
        artifact.seek(0)
        artifact.write(json.dumps(report, indent=2) + "\n")
        artifact.truncate()
        artifact.flush()

    def invoked():
        report["runtime_respond_exercised"] = True

    try:
        persist("running")
        with tempfile.TemporaryDirectory(prefix="local-runtime-eval-") as directory:
            world = await open_world(str(Path(directory) / "eval.db"), with_repo=False)
            try:
                async with world.session_factory() as db:
                    gateway = await pinned_gateway(world, db, model)
                    session = await sessions.start(
                        db, world.learner_id, mode=Mode.STEADY, energy=3
                    )
                    for name, body, criteria in cases(session.id):
                        report["results"].append(
                            await evaluate_case(
                                db,
                                gateway,
                                world.learner_id,
                                name,
                                body,
                                criteria,
                                world.settings,
                                on_respond=invoked,
                            )
                        )
                        persist("running")
                persist("completed")
            finally:
                await world.close()
    except BaseException:
        persist("interrupted_or_failed")
        raise
    finally:
        artifact.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--model", choices=["llama31-8b", "gemma3-12b"], default="llama31-8b"
    )
    args = parser.parse_args()
    asyncio.run(run(args.out, args.model))
