#!/usr/bin/env python3
"""Explicit paid comparison of synthetic feedback cases, charged to the live app budget.

Never run alongside another paid CLI evaluation. The app's single-process reservation
lock does not serialize independent CLI processes; live reservation rows remain visible.
No learner material is read, no session/evidence is created, and routing is unchanged.
"""

import argparse
import asyncio
import hashlib
import json
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import select

from app.core.config import get_settings
from app.db.models import ModelCall
from app.db.session import make_engine, make_session_factory
from app.evals.grounded_feedback import bound_feedback
from app.models_ai.benchmark_gateway import BenchmarkRouter
from app.models_ai.budget import Budget
from app.models_ai.factory import build_providers
from app.models_ai.gateway import ModelGateway
from app.models_ai.provider import TaskClass
from app.models_ai.registry import get_row, get_spec
from app.orchestrator.playground import messages
from app.schemas.playground import PlaygroundRequest
from eval_quoted_feedback import CASES


async def run(output: Path) -> None:
    settings = get_settings()
    if not settings.openai_api_key:
        raise ValueError("Configure the existing server-side key locally first")
    task_prompt = (
        Path(__file__).resolve().parents[1] / "prompts/playground/quoted-feedback.v1.md"
    ).read_text()
    engine = make_engine(settings.database_url_resolved)
    evaluation_id = str(uuid.uuid4())
    results = []
    report = {
        "synthetic": True,
        "pinned_model": "openai-luna",
        "fallback_allowed": False,
        "live_integration": False,
        "maximum_incremental_budget_usd": 0.02,
        "task_prompt_sha256": hashlib.sha256(task_prompt.encode()).hexdigest(),
        "results": results,
    }

    def persist(status: str) -> None:
        report["status"] = status
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n")

    persist("running")
    try:
        async with make_session_factory(engine)() as db:
            row, spec = (
                await get_row(db, "openai-luna"),
                await get_spec(db, "openai-luna"),
            )
            if (
                row.status != "ready"
                or spec.provider != "openai"
                or spec.model != "gpt-6-luna"
            ):
                raise ValueError(
                    "The configured evaluation candidate must be ready GPT-6 Luna"
                )
            if spec.price_in_per_mtok < 0.125 or spec.price_out_per_mtok < 0.5:
                raise ValueError(
                    "Registry rates must cover the verified short-context price ceilings"
                )
            initial = await Budget(settings.daily_budget_usd).spend_today(db)
            if initial.open_reservations:
                raise ValueError(
                    "Wait for existing hosted reservations before this CLI comparison"
                )
            cap = min(settings.daily_budget_usd, initial.counted + 0.02)
            budget = Budget(cap)
            report["effective_daily_cap_usd"] = cap
            report["prior_counted_spend_usd"] = initial.counted
            await db.rollback()
            gateway = ModelGateway(
                db,
                BenchmarkRouter("openai-luna"),
                {"openai": build_providers(settings)["openai"]},
                budget,
            )
            for name, exercise, answer, mode, criteria in CASES:
                body = PlaygroundRequest(
                    session_id="eval",
                    exercise=exercise,
                    code="",
                    learner_answer=answer,
                    questioning_style=mode,
                    question="Review my reasoning against the supplied task.",
                )
                packet = messages(body)
                packet[0] = packet[0].model_copy(
                    update={"content": packet[0].content + "\n\n" + task_prompt}
                )
                schema = bound_feedback(answer, socratic=mode == "socratic")
                result = {
                    "case": name,
                    "review_criteria": criteria,
                    "request": body.model_dump(exclude={"session_id"}),
                    "messages_sha256": hashlib.sha256(
                        json.dumps(
                            [m.model_dump() for m in packet],
                            sort_keys=True,
                            ensure_ascii=False,
                        ).encode()
                    ).hexdigest(),
                }
                started = time.perf_counter()
                try:
                    reply = await asyncio.wait_for(
                        gateway.complete(
                            TaskClass.EXPLAIN_SIMPLE,
                            packet,
                            response_model=schema,
                            max_tokens=650,
                            metadata={
                                "task": "quoted_feedback_eval",
                                "case": name,
                                "evaluation_id": evaluation_id,
                            },
                        ),
                        timeout=120,
                    )
                    checked = schema.model_validate_json(reply.result.text)
                    result.update(
                        {
                            "literal_contract_valid": True,
                            "model": reply.registry_id,
                            "feedback": checked.model_dump(),
                            "raw_text": reply.result.text,
                        }
                    )
                except Exception as exc:
                    await db.rollback()
                    result.update(
                        {
                            "literal_contract_valid": False,
                            "error_type": type(exc).__name__,
                        }
                    )
                calls = list(
                    await db.scalars(
                        select(ModelCall).where(
                            ModelCall.metadata_json["evaluation_id"].as_string()
                            == evaluation_id,
                            ModelCall.metadata_json["case"].as_string() == name,
                        )
                    )
                )
                result["attempts"] = [
                    {
                        "model": c.model,
                        "outcome": c.outcome,
                        "tokens_in": c.tokens_in,
                        "tokens_out": c.tokens_out,
                        "cost_usd": c.cost_usd,
                        "cost_status": c.cost_status,
                        "reserved_usd": c.reserved_usd,
                    }
                    for c in calls
                ]
                result["elapsed_ms"] = round((time.perf_counter() - started) * 1000)
                results.append(result)
                budget_blocked = any(c.outcome == "blocked" for c in calls)
                await db.rollback()
                persist("running")
                print(name, result["literal_contract_valid"], flush=True)
                if budget_blocked:
                    persist("budget_blocked")
                    return
        persist("completed")
    except BaseException:
        persist("interrupted_or_failed")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--allow-paid",
        action="store_true",
        help="Explicitly permit a paid synthetic comparison within existing budget and a $0.02 incremental limit",
    )
    args = parser.parse_args()
    if not args.allow_paid:
        parser.error(
            "Paid comparison requires --allow-paid; local diagnostic is the default alternative"
        )
    asyncio.run(run(args.out))
