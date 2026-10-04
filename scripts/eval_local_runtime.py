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

from sqlalchemy import select

from app.core.config import get_settings
from app.db.models import ModelCall, TutorAnswer
from app.evals.harness import open_world
from app.kernel import session as sessions
from app.models_ai.benchmark_gateway import BenchmarkRouter
from app.models_ai.gateway import REPAIR_POLICY_VERSION
from app.models_ai.provider import safe_structured_reason
from app.models_ai.registry import get_row, get_spec
from app.orchestrator import playground
from app.schemas.common import Mode
from app.schemas.playground import PlaygroundContext, PlaygroundRequest


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
        started = time.perf_counter()
        try:
            result = await self.gateway.complete(task, messages, **kwargs)
            record["raw_final_model_text"] = result.result.text
            record["outcome"] = "completed"
            return result
        except BaseException:
            record["outcome"] = "failed_or_cancelled"
            raise
        finally:
            record["elapsed_ms"] = round((time.perf_counter() - started) * 1000)
            record["timing_scope"] = "gateway wall time including retries; not per-attempt latency"


def basic_cases(session_id):
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


def notebook_cases(session_id):
    """Frozen synthetic notebook tasks; supplied outputs are fixtures, never executed evidence."""

    def request(target, exercise, answer, code="", output="", **kwargs):
        return PlaygroundRequest(
            session_id=session_id,
            intent="check_answer",
            question="Review my reasoning against the supplied notebook task and evidence.",
            exercise=exercise,
            learner_answer=answer,
            code=code,
            output=output,
            learning_context=PlaygroundContext(target_id="synthetic-notebook-" + target),
            **kwargs,
        )

    missing = request(
        "missingness",
        "One row is one participant. Group A has 80 participants, 20 missing income; "
        "B has 20 participants, 10 missing income. Compare within-group income missingness rates.",
        "A has 20% missing income and B has 10%, using all 100 participants as denominator.",
        "missing = df.groupby('group')['income'].apply(lambda values: values.isna().sum())",
        "Supplied synthetic output: missing income counts\nA 20\nB 10",
    )
    return [
        (
            "group_denominators",
            missing,
            (
                "Reject pooled denominators for within-group rates: A=20/80=25%, B=10/20=50%. "
                "Counts alone do not mean A has a higher missingness rate."
            ),
        ),
        (
            "corrected_denominators",
            missing.model_copy(
                update={
                    "prefer_saved": True,
                    "learner_answer": "I corrected my denominator: A is 20/80 = 25%, B is 10/20 = 50%. "
                    "B has the higher within-group missingness rate despite fewer missing rows.",
                }
            ),
            (
                "Accept the corrected reasoning; do not reuse criticism of the earlier answer. "
                "Do not infer the code calculated rates: its supplied output contains counts only."
            ),
        ),
        (
            "bin_boundary",
            request(
                "bins",
                "Required bins: [0,18), [18,65), [65,120). Evaluate the code for ages 18 and 65.",
                "This pd.cut call places 18 in the adult bin and 65 in the older bin.",
                "pd.cut(ages, bins=[0,18,65,120], labels=['young','adult','older'], right=True, include_lowest=True)",
            ),
            (
                "Reject claim for right=True: 18 falls in first bin and 65 in second. "
                "Explain right=False matches required left-closed/right-open bins; do not claim execution."
            ),
        ),
        (
            "cleaning_representation",
            request(
                "cleaning",
                "Before complete-case cleaning: A=80 rows, B=20. After: A=72, B=8. "
                "Overall held-out accuracy increases from 0.80 to 0.85. Is this enough to conclude fairness?",
                "Accuracy improved and we used the same rule, so cleaning was fair to both groups.",
            ),
            (
                "Challenge equal-rule/overall-accuracy inference: retention A=90%, B=40%; "
                "B representation changes from20% to10%. Ask for group-level errors/missingness evidence "
                "as a next step, without claiming the model is definitively unfair or creating an explicit-mode quiz."
            ),
        ),
        (
            "unrun_pandas",
            request(
                "unrun",
                "Remove rows missing income only; retain rows whose optional nickname is missing. "
                "No execution output was supplied.",
                "df.dropna() removes only missing income, so it satisfies the task.",
                "cleaned = df.dropna()",
            ),
            (
                "Explain dropna() without subset considers all columns; suggest subset=['income']. "
                "Do not assert dataset results or successful execution."
            ),
        ),
        (
            "contradictory_output",
            request(
                "output",
                "Check the claim against supplied output for this notebook cell. "
                "The output is learner-supplied, not independently verified.",
                "The cell ran successfully and created a cleaned DataFrame.",
                "cleaned = df.dropna(subset=['income'])",
                "Traceback (most recent call last):\nKeyError: ['income']",
            ),
            (
                "Reject success claim because supplied output is KeyError, not a DataFrame; "
                "suggest inspecting actual column names. Do not invent a corrected column or execution."
            ),
        ),
        (
            "stale_output",
            request(
                "stale",
                "The code was edited after the supplied output. Assess whether current code works.",
                "The earlier output proves the edited cleaning code works.",
                "cleaned = df.dropna(subset=['income'])\nprint(len(cleaned))",
                "80",
                output_stale=True,
            ),
            (
                "State stale output cannot verify current code or retained count. "
                "Recommend rerunning current cell; never claim a fresh successful run."
            ),
        ),
        (
            "data_dictionary",
            request(
                "dictionary",
                "Create a data dictionary for rows representing participants. "
                "Columns: participant_id (identifier), age_years (integer years), income (optional currency amount), "
                "group (categorical label). Income missingness is unknown, not documented as zero income.",
                "participant_id is a continuous measurement; missing income always means zero income.",
            ),
            (
                "Correct identifier-versus-measurement distinction and reject equating unknown income with zero. "
                "Describe units, types and missing-value meaning without inventing dataset statistics."
            ),
        ),
    ]


def reasoning_cases(session_id):
    """Synthetic reasoning checks independent of code execution and model grading."""
    original = next(
        case for case in notebook_cases(session_id) if case[0] == "cleaning_representation"
    )

    def request(target, exercise, answer, **kwargs):
        return PlaygroundRequest(
            session_id=session_id,
            intent="check_answer",
            prefer_saved=False,
            questioning_style="explicit",
            question="Review my reasoning against the supplied task and evidence.",
            exercise=exercise,
            learner_answer=answer,
            code="",
            output="",
            learning_context=PlaygroundContext(target_id="synthetic-reasoning-" + target),
            **kwargs,
        )

    task = "A dataset starts with 50 rows and retains 30. What proportion remains?"
    return [
        original,
        (
            "cleaning_counts_vs_rates",
            request(
                "counts-vs-rates",
                "Before cleaning: A=200 rows, B=40. After cleaning: A=160, B=20. Compare proportional impact.",
                "A lost 40 and B lost 20, so A was proportionally more affected.",
            ),
            "Accept removed counts 40 and 20; reject proportional conclusion. Removal A=20%, B=50%; "
            "retention A=80%, B=50%. Distinguish counts from rates without inventing fairness evidence.",
        ),
        (
            "cleaning_equal_retention",
            request(
                "equal-retention",
                "Before cleaning: A=120 rows, B=40. After cleaning: A=90, B=30. Is retention enough to conclude "
                "fairness?",
                "Both retained 75%, so cleaning was definitely fair.",
            ),
            "Accept 75% retention for both and unchanged representation A=75%, B=25%. Reject definite "
            "fairness; group-level errors and missingness mechanisms still need evidence.",
        ),
        (
            "quoted_mistake_runtime",
            request(
                "quoted-mistake",
                task,
                "The claim '30/50 = 0.9' is wrong. The correct proportion is 60%.",
            ),
            "Accept the learner's rejection of the quoted error and correct 60%; do not attribute the quoted "
            "0.9 claim as their endorsed answer.",
        ),
        (
            "revised_answer_runtime",
            request(
                "revised-answer",
                task,
                "I revised my earlier answer: 30/50 = 0.6, or 60%.",
                history=[
                    {"role": "user", "text": "30/50 = 0.9, so 90%."},
                    {"role": "assistant", "text": "That is correct; 90% remain."},
                ],
            ),
            "Accept current revised 60% answer. Identify earlier tutor endorsement of 90% as incorrect if "
            "discussed; do not grade the old answer as current or repeat the prior tutor error.",
        ),
    ]


def cases(session_id, suite="basic"):
    if suite == "basic":
        return basic_cases(session_id)
    if suite == "notebook":
        return notebook_cases(session_id)
    if suite == "reasoning":
        return reasoning_cases(session_id)
    raise ValueError("Unknown diagnostic suite")


def suite_manifest(suite):
    fixtures = [
        {
            "case": name,
            "request": body.model_dump(exclude={"session_id"}),
            "criteria": criteria,
        }
        for name, body, criteria in cases("manifest", suite)
    ]
    return {
        "suite": suite,
        "suite_version": 1,
        "case_count": len(fixtures),
        "fixture_sha256": hashlib.sha256(
            json.dumps(fixtures, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest(),
        "evidence_provenance": "synthetic supplied text/code/output; diagnostic executes no notebook code",
    }


def attempt_diagnostic(call):
    """Allowlist accounting fields; never export raw errors or arbitrary metadata.

    Gateway failures may log a default zero without measuring provider latency.
    Zero cannot distinguish missing measurement from a sub-millisecond result.
    """
    result = {
        key: getattr(call, key)
        for key in (
            "registry_id",
            "model",
            "provider",
            "task",
            "request_id",
            "attempt",
            "outcome",
            "tokens_in",
            "tokens_out",
            "cost_usd",
        )
    }
    metadata = getattr(call, "metadata_json", None)
    result["structured_reason_code"] = safe_structured_reason(
        metadata.get("structured_reason_code") if isinstance(metadata, dict) else None
    )
    known = isinstance(call.latency_ms, (int, float)) and call.latency_ms > 0
    result["latency_ms"] = call.latency_ms if known else None
    result["latency_source"] = "gateway_record" if known else "unavailable"
    return result


async def evaluate_case(
    db, gateway, learner_id, name, body, criteria, settings, on_respond=None, repo=None
):
    before = set(await db.scalars(select(ModelCall.id)))
    recorder = RecordedGateway(gateway)
    result = {
        "case": name,
        "request": body.model_dump(exclude={"session_id"}),
        "manual_review_criteria": criteria,
        "semantic_review": "not_reviewed",
        "timing_scope": "respond and result lookup or failure rollback; excludes attempt accounting query",
        "gateway_requests": recorder.requests,
    }
    started = time.perf_counter()
    try:
        if on_respond is not None:
            on_respond()
        reply = await asyncio.wait_for(
            playground.respond(db, recorder, learner_id, body, settings=settings, repo=repo),
            timeout=120,
        )
        result["reply"] = reply.model_dump()
        result["status"] = "completed"
        saved = await db.get(TutorAnswer, reply.answer_id) if reply.answer_id else None
        result["saved_metadata"] = saved.metadata_json if saved else None
        result["literal_schema_validated_this_run"] = (
            body.intent == "check_answer" and not reply.reused and reply.route != "deterministic"
        )
    except Exception as exc:  # noqa: BLE001 — retain each failure without hiding later cases
        await db.rollback()
        result.update(status="failed", error_type=type(exc).__name__)
        result["literal_schema_validated_this_run"] = None
    result["elapsed_ms"] = round((time.perf_counter() - started) * 1000)
    calls = list(await db.scalars(select(ModelCall).where(ModelCall.id.not_in(before))))
    result["attempts"] = [attempt_diagnostic(call) for call in calls]
    return result


async def run(output, model, suite="basic"):
    started = time.perf_counter()
    local_settings(get_settings())  # reject remote host before harness discovery
    report = {
        "report_version": 3,
        **suite_manifest(suite),
        "synthetic": True,
        "pinned_feedback_generation_model": model,
        "ancillary_models": "local embedding lookup may use a different local model",
        "runtime_respond_exercised": False,
        "production_routing_exercised": False,
        "fallback_allowed": False,
        "runtime_prompt_version": playground.VERSION,
        "feedback_wire_contract": "passage_selection.v1",
        "structured_repair_policy_version": REPAIR_POLICY_VERSION,
        "scope": "ordered synthetic runtime cases, not a quality or latency benchmark",
        "timing_scope": "run wall time up to report serialization; completed status precedes final world cleanup",
        "results": [],
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    # Reserve before setup; never truncate an existing artifact or follow an existing symlink.
    artifact = output.open("x")

    def persist(status):
        report["status"] = status
        report["elapsed_ms"] = round((time.perf_counter() - started) * 1000)
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
                    session = await sessions.start(db, world.learner_id, mode=Mode.STEADY, energy=3)
                    for name, body, criteria in cases(session.id, suite):
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
    parser.add_argument("--suite", choices=["basic", "notebook", "reasoning"], default="basic")
    parser.add_argument(
        "--model", choices=["llama31-8b", "gemma3-12b", "gemma3-27b"], default="llama31-8b"
    )
    args = parser.parse_args()
    asyncio.run(run(args.out, args.model, args.suite))
