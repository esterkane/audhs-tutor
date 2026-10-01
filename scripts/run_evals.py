#!/usr/bin/env python3
"""Tutoring-quality evals: hard checks on real tutor turns (+ rubric judge when `hosted-medium` is ready).
usage: run_evals.py [--cases "evals/cases/*.yaml"] [--out evals/results/latest.json]
Runs against data/evals.db (isolated) and the production Qdrant corpus."""

import argparse
import asyncio
import glob
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from pydantic import BaseModel, Field  # noqa: E402

from app.db.models import LearnerPreference  # noqa: E402
from app.evals.hardchecks import run_hard_checks  # noqa: E402
from app.evals.harness import open_world, results_dir  # noqa: E402
from app.kernel import session as ksession  # noqa: E402
from app.kernel import skill_graph  # noqa: E402
from app.models_ai import registry  # noqa: E402
from app.models_ai.provider import Message, TaskClass  # noqa: E402
from app.orchestrator.tutor import TutorTurn  # noqa: E402
from app.schemas.common import Mode  # noqa: E402
from app.schemas.tutor import TurnRequest  # noqa: E402

RUBRIC = ["cognitive_load", "active_learning", "metacognition", "curiosity", "adaptivity"]


class RubricScore(BaseModel):
    cognitive_load: int = Field(ge=1, le=5)
    active_learning: int = Field(ge=1, le=5)
    metacognition: int = Field(ge=1, le=5)
    curiosity: int = Field(ge=1, le=5)
    adaptivity: int = Field(ge=1, le=5)
    evidence: str


async def judge(world: Any, db: Any, case: dict[str, Any], answer: str) -> dict[str, Any] | None:
    try:
        row = await registry.get_row(db, "hosted-medium")
    except KeyError:
        return None
    if row.status != "ready":
        return None
    prompt = (
        "Score this tutor turn 1-5 on LearnLM's five principles (manage cognitive load, inspire active learning, "
        "deepen metacognition, stimulate curiosity, adapt to the learner). Quote evidence.\n\n"
        f"Learner: {case['turns'][0]['learner']}\n\nTutor: {answer}"
    )
    out = await world.gateway(db).complete(
        TaskClass.JUDGE,
        [Message(role="user", content=prompt)],
        response_model=RubricScore,
        learner_id=world.learner_id,
        max_tokens=400,
    )
    return out.result.parsed.model_dump() if out.result.parsed else None


async def run_case(world: Any, path: Path) -> dict[str, Any]:
    case = yaml.safe_load(path.read_text())  # noqa: ASYNC240 (one-off tooling)
    async with world.session_factory() as db:
        node = await skill_graph.get_node_by_slug(db, case["skill"])
        assert node, f"unknown skill {case['skill']}"
        s = await ksession.start(
            db,
            world.learner_id,
            mode=Mode.STEADY,
            energy=3,
            socratic=case.get("questioning_style") == "socratic",
        )
        turn = TutorTurn(db, world.gateway(db), world.repo)
        results = []
        for t in case["turns"]:
            text, done, meta = "", None, None
            async for kind, data in turn.run(
                TurnRequest(
                    session_id=s.id,
                    text=t["learner"],
                    skill_id=node.id,
                    action=t.get("action", "auto"),
                )
            ):
                if kind == "meta":
                    meta = data
                elif kind == "token":
                    text += data["text"]
                elif kind == "done":
                    done = data
            assert done and meta
            checks = run_hard_checks(
                text,
                action=meta["action"],
                questioning_style=meta["questioning_style"],
                sources=done["sources"],
                expect=case["expect"]["hard"],
            )
            rubric = await judge(world, db, case, text) if case["expect"].get("rubric") else None
            results.append(
                {
                    "learner": t["learner"],
                    "action": meta["action"],
                    "text": text,
                    "sources": [x["citation"] for x in done["sources"]],
                    "hard": checks,
                    "hard_pass": all(checks.values()),
                    "rubric": rubric,
                    "latency_ms": done["latency_ms"],
                    "model": done["registry_id"],
                }
            )
        await ksession.end(db, s.id, energy_after=3, self_report=3)
        # keep the eval learner's routing default
        await db.execute(
            LearnerPreference.__table__.delete().where(
                LearnerPreference.learner_id == world.learner_id
            )
        )
        await db.commit()
    return {
        "id": case["id"],
        "skill": case["skill"],
        "turns": results,
        "hard_pass": all(r["hard_pass"] for r in results),
    }


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cases", default=str(ROOT / "evals" / "cases" / "*.yaml"))
    ap.add_argument("--out", default=str(results_dir() / "latest.json"))
    args = ap.parse_args()
    world = await open_world("evals.db")
    try:
        cases = sorted(glob.glob(args.cases))
        out: dict[str, Any] = {
            "ran_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "cases": [],
        }
        for p in cases:
            res = await run_case(world, Path(p))
            out["cases"].append(res)
            flag = "PASS" if res["hard_pass"] else "FAIL"
            failed = [k for r in res["turns"] for k, v in r["hard"].items() if not v]
            print(
                f"[{flag}] {res['id']}: {res['turns'][0]['model']} {res['turns'][0]['latency_ms']} ms {failed or ''}"
            )
        n = len(out["cases"])
        passed = sum(1 for c in out["cases"] if c["hard_pass"])
        out["summary"] = {
            "cases": n,
            "hard_pass": passed,
            "hard_pass_rate": round(passed / n, 3) if n else None,
        }
        baseline_path = results_dir() / "baseline.json"
        if baseline_path.exists():
            base = json.loads(baseline_path.read_text())
            out["summary"]["baseline_hard_pass_rate"] = base.get("summary", {}).get(
                "hard_pass_rate"
            )
        Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False))  # noqa: ASYNC240
        print(f"hard checks: {passed}/{n} → {args.out}")
        return 0 if passed == n else 1
    finally:
        await world.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
