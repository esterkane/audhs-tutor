#!/usr/bin/env python3
"""Stage 1 benchmark (docs/ROADMAP.md). Run: make bench s=1
Runs 3 simulated sessions on attention against data/bench.db (isolated; the learner's dev.db is untouched)
with real local models and the production Qdrant corpus.
  A every tutor turn has a tutor_trace (with model_call + retrieval_trace)
  B every attempt yields competency evidence + an FSRS update (review_log)
  C a delayed review 2 days later works (due queue non-empty, rating grows stability)
  D hard-check evals pass (scripts/run_evals.py hard checks, rate >= 0.75)
  E learning loop usefulness signal: mastery rises across sessions; p50 turn latency
"""

import asyncio
import json
import statistics
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import func, select  # noqa: E402

from app.db import models  # noqa: E402
from app.evals.harness import open_world, results_dir  # noqa: E402
from app.kernel import (  # noqa: E402
    competency,
    memory,
    skill_graph,  # noqa: E402
)
from app.kernel import session as ksession  # noqa: E402
from app.orchestrator.grader import Grader  # noqa: E402
from app.orchestrator.tutor import TutorTurn  # noqa: E402
from app.schemas.common import Mode  # noqa: E402
from app.schemas.grading import AttemptRequest  # noqa: E402
from app.schemas.tutor import TurnRequest  # noqa: E402

results: dict[str, dict[str, Any]] = {}
GOOD_ANSWERS = {
    "explain_back": (
        "The dot product is large when two vectors point in a similar direction (it is |a||b| cos of the angle), "
        "scaling a vector scales the product, and with random entries it grows with the dimension because the "
        "variance adds up; softmax turns scores into positive weights that sum to one where only differences "
        "matter and the largest score dominates, and very large scores saturate it into a one-hot with tiny gradients. "
        "A query asks a question, each key is matched against it with a dot product to get a score, "
        "softmax turns the scores into weights, and the weights combine the values into the output; "
        "the variance of the dot product grows with d_k so dividing by sqrt(d_k) restores unit variance "
        "and keeps softmax from saturating with tiny gradients; keys and values of past tokens are stored "
        "per layer so each step only computes the new token, giving O(n) per step; a padding mask hides "
        "pad tokens and a causal mask hides future positions, both applied before softmax."
    )
}


def record(key: str, status: str, **data: Any) -> None:
    results[key] = {"status": status, **data}
    print(f"[{status:4}] {key}: {json.dumps(data, default=str)}", flush=True)


async def run_session(world: Any, i: int, now: datetime) -> dict[str, Any]:
    async with world.session_factory() as db:
        gw = world.gateway(db)
        s = await ksession.start(db, world.learner_id, mode=Mode.STEADY, energy=3)
        turn = TutorTurn(db, gw, world.repo)
        node = await skill_graph.next_skill(db, world.learner_id)
        assert node
        latencies = []
        for text, action in (
            (f"Explain the core idea of {node.title}.", "explain"),
            ("I'm stuck, give me a hint.", "hint"),
        ):
            done = None
            async for kind, data in turn.run(
                TurnRequest(session_id=s.id, text=text, skill_id=node.id, action=action)
            ):
                if kind == "done":
                    done = data
            assert done
            latencies.append(done["latency_ms"])
        grader = Grader(db, gw)
        attempts = 0
        for k in range(3):
            a = await grader.next_item(world.learner_id, node.id)
            if a is None:
                break
            if a.kind == "mcq":
                # a realistic learner: the second session gets its first MCQ wrong (-> Again -> due soon)
                wrong = (int(a.item_json["answer"]) + 1) % len(a.item_json["options"])
                answer = str(wrong if (i == 1 and k == 0) else a.item_json["answer"])
            elif a.kind == "cloze":
                answer = a.item_json["answers"][0]
            else:
                answer = GOOD_ANSWERS["explain_back"]
            await grader.grade(
                AttemptRequest(
                    session_id=s.id,
                    assessment_id=a.id,
                    answer=answer,
                    confidence_pre=4,
                    latency_ms=5000,
                ),
                now=now,
            )
            attempts += 1
        mastery = await competency.mastery(db, world.learner_id, node.id)
        await ksession.end(db, s.id, energy_after=3, self_report=4)
        return {
            "session": s.id,
            "skill": node.slug,
            "turns": 2,
            "attempts": attempts,
            "mastery": round(mastery, 3),
            "latencies": latencies,
        }


async def main() -> int:
    world = await open_world("bench.db", fresh=True)
    now = datetime.now(UTC)
    try:
        sessions = [await run_session(world, i, now) for i in range(3)]
        async with world.session_factory() as db:
            n_turn_events = (
                await db.execute(
                    select(func.count())
                    .select_from(models.LearningEvent)
                    .where(models.LearningEvent.verb == "explained")
                )
            ).scalar_one()
            traces = (await db.execute(select(models.TutorTrace))).scalars().all()
            full = [t for t in traces if t.model_call_id and t.retrieval_trace_id]
            record(
                "A every turn has a tutor_trace",
                "PASS" if len(traces) == n_turn_events == len(full) == 6 else "FAIL",
                turns=n_turn_events,
                traces=len(traces),
                with_model_call_and_retrieval=len(full),
            )

            attempts = (
                await db.execute(select(func.count()).select_from(models.AssessmentAttempt))
            ).scalar_one()
            evidence = (
                await db.execute(select(func.count()).select_from(models.CompetencyEvidence))
            ).scalar_one()
            logs = (
                await db.execute(select(func.count()).select_from(models.ReviewLog))
            ).scalar_one()
            states = (
                await db.execute(select(func.count()).select_from(models.CompetencyState))
            ).scalar_one()
            record(
                "B every attempt -> evidence + FSRS update",
                "PASS" if attempts > 0 and attempts == evidence == logs and states > 0 else "FAIL",
                attempts=attempts,
                evidence_rows=evidence,
                review_logs=logs,
                competency_states=states,
            )

            later = now + timedelta(days=2)
            due_now = await memory.due_items(
                db, world.learner_id, now=now + timedelta(minutes=1), cap=100
            )
            due_later = await memory.due_items(db, world.learner_id, now=later, cap=100)
            ok = bool(due_later)
            stability_delta = None
            if due_later:
                item, ms = due_later[0]
                before = ms.stability
                await memory.review(db, world.learner_id, item.id, 3, now=later, latency_ms=3000)
                await db.refresh(ms)
                stability_delta = round((ms.stability or 0) - (before or 0), 3)
                ok = (
                    ok
                    and (ms.stability or 0) > (before or 0)
                    and datetime.fromisoformat(ms.due) > later
                )
            record(
                "C delayed review 2 days later",
                "PASS" if ok else "FAIL",
                due_in_1_min=len(due_now),
                due_in_2_days=len(due_later),
                stability_delta=stability_delta,
            )

        proc = subprocess.run(  # noqa: ASYNC221 (sequential tooling)
            [sys.executable, str(ROOT / "scripts" / "run_evals.py")],
            capture_output=True,
            text=True,
            cwd=ROOT / "backend",
        )
        summary = {}
        try:
            summary = json.loads((results_dir() / "latest.json").read_text()).get("summary", {})
        except Exception:
            pass
        rate = summary.get("hard_pass_rate")
        record(
            "D hard-check evals",
            "PASS" if rate is not None and rate >= 0.75 else "FAIL",
            **summary,
            evals_tail=proc.stdout.strip().splitlines()[-6:],
        )

        lat = [x for s in sessions for x in s["latencies"]]
        masteries = [s["mastery"] for s in sessions]
        record(
            "E loop signal",
            "PASS" if masteries[-1] > 0 and max(masteries) >= 0.3 else "FAIL",
            sessions=sessions,
            turn_latency_p50_ms=int(statistics.median(lat)) if lat else None,
            turn_latency_max_ms=max(lat) if lat else None,
        )
    finally:
        await world.close()
    out = results_dir() / "bench_stage1.json"
    out.write_text(json.dumps(results, indent=2, default=str))
    failed = [k for k, v in results.items() if v["status"] == "FAIL"]
    print(
        "\nSTAGE 1 BENCHMARK:",
        "FAIL" if failed else "PASS",
        f"({len(results)} checks, {len(failed)} failed)",
    )
    print(f"written: {out}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
