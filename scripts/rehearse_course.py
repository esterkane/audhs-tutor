#!/usr/bin/env python3
"""Rehearse the learning loop on one course — on a private snapshot of the configured database.

  rehearse_course.py --course NAME [--sessions N] [--json]

What it does, on `data/rehearsal.db` (an online-backup copy of the configured SQLite file; the
live database is never written): publishes every open draft of the course, sets `goal.course`,
then runs N sessions, each on the skill the kernel would teach next (the same skill stays current
until it is mastered, exactly as the learner would meet it) — an explain turn and a
hint turn with the routed local model (hosted providers off, budget 0), the assessment rotation
(MCQ answered right, cloze answered from the key, one explain-back), competency refresh, the FSRS
due queue, a confidence-rated session end — and reports what a learner would meet after publishing
for real: citations and whether they belong to the course, grader levels used, mastery, latencies,
and every exception. Results go to `evals/results/rehearse_<course>.json`.
"""

import argparse
import asyncio
import contextlib
import json
import re
import sqlite3
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import func, select  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db import models  # noqa: E402
from app.db.migrate import upgrade_to_head  # noqa: E402
from app.db.session import make_engine, make_session_factory  # noqa: E402
from app.evals.harness import World, results_dir  # noqa: E402
from app.kernel import competency, curriculum, memory, preferences, skill_graph  # noqa: E402
from app.kernel import session as ksession  # noqa: E402
from app.kernel.learner import get_or_create_owner  # noqa: E402
from app.knowledge.reindex import build_repo  # noqa: E402
from app.orchestrator.grader import Grader  # noqa: E402
from app.orchestrator.tutor import TutorTurn  # noqa: E402
from app.schemas.common import Mode  # noqa: E402
from app.schemas.grading import AttemptRequest  # noqa: E402
from app.schemas.tutor import TurnRequest  # noqa: E402

SNAPSHOT = ROOT / "data" / "rehearsal.db"


def snapshot(sync_url: str, dest: Path) -> None:
    """Online backup of the configured DB; the source is opened read-only."""
    src = sync_url.replace("sqlite:///", "", 1)
    for p in (dest, dest.with_name(dest.name + "-wal"), dest.with_name(dest.name + "-shm")):
        if p.exists():
            p.unlink()
    with (
        contextlib.closing(sqlite3.connect(f"file:{src}?mode=ro", uri=True)) as a,
        contextlib.closing(sqlite3.connect(dest)) as b,
    ):
        a.backup(b)


async def open_snapshot_world() -> World:
    base = get_settings()
    if base.sync_database_url.replace("sqlite:///", "", 1).endswith("rehearsal.db"):
        raise SystemExit(
            "DATABASE_URL already points at the rehearsal copy; point it at the live DB"
        )
    snapshot(base.sync_database_url, SNAPSHOT)
    settings = base.model_copy(
        update={
            "database_url": f"sqlite+aiosqlite:///{SNAPSHOT}",
            "auto_migrate": False,
            "anthropic_api_key": "",  # local models only: nothing hosted, nothing paid
            "daily_budget_usd": 0.0,
        }
    )
    upgrade_to_head(settings.sync_database_url)
    engine = make_engine(settings.database_url_resolved)
    factory = make_session_factory(engine)
    async with factory() as db:
        learner = await get_or_create_owner(db)
        repo = await build_repo(db, settings)
    return World(settings, engine, factory, learner.id, repo)


def explain_back_answer(goal: str, concept: str) -> str:
    """A plausible learner explanation built only from the published goal: what a learner who
    read the lesson goal once might say. Grading it exercises the rubric/LLM path honestly."""
    core = re.sub(
        r"^(understand|learn|describe|identify|explain)\s+(how\s+to\s+)?", "", goal, flags=re.I
    )
    return (
        f"In my own words: {concept} is about {core.rstrip('.')}. The key idea is that the steps "
        f"depend on each other, so I would first set up the inputs, then apply the method from the "
        f"lecture, and finally check the output against what the lecture expects."
    )


async def rehearse_skill(
    world: World, node: models.SkillNode, obj: models.LearningObject | None
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "skill": node.slug,
        "title": node.title,
        "course": node.course,
        "problems": [],
    }
    async with world.session_factory() as db:
        gw = world.gateway(db)
        s = await ksession.start(db, world.learner_id, mode=Mode.STEADY, energy=3)
        assert world.repo is not None  # opened with the production Qdrant adapter
        turn = TutorTurn(db, gw, world.repo)
        turns: list[dict[str, Any]] = []
        for text, action in (
            (f"Explain the core idea of {node.title}.", "explain"),
            ("I'm stuck, give me a hint.", "hint"),
        ):
            t0 = time.perf_counter()
            done: dict[str, Any] | None = None
            meta: dict[str, Any] | None = None
            tokens: list[str] = []
            try:
                async for kind, data in turn.run(
                    TurnRequest(session_id=s.id, text=text, skill_id=node.id, action=action)
                ):
                    if kind == "meta":
                        meta = data
                    elif kind == "token":
                        tokens.append(
                            str(data.get("text", data) if isinstance(data, dict) else data)
                        )
                    elif kind == "done":
                        done = data
                    elif kind == "error":
                        out["problems"].append(f"{action}: tutor error {data}")
            except Exception as e:  # noqa: BLE001 — a rehearsal reports, it does not crash
                out["problems"].append(f"{action}: {type(e).__name__}: {str(e)[:200]}")
                continue
            answer = "".join(tokens)
            sources = (meta or {}).get("sources") or (done or {}).get("sources") or []
            cited_ids = [
                src.get("chunk_id") for src in sources if isinstance(src, dict) and src.get("cited")
            ]
            foreign = 0
            for cid in cited_ids:
                p = await curriculum.passage(db, cid) if cid else None
                if p is None or p.course != node.course:
                    foreign += 1
            citations_in_text = len(re.findall(r"\[\d+\]", answer))
            rec = {
                "action": action,
                "latency_s": round(time.perf_counter() - t0, 2),
                "model": (done or {}).get("registry_id"),
                "route": (done or {}).get("route"),
                "outcome": (done or {}).get("outcome"),
                "retrieved": len(sources),
                "cited": len(cited_ids),
                "cited_outside_course": foreign,
                "citation_marks_in_text": citations_in_text,
                "answer_chars": len(answer),
                "answer_head": answer[:240].replace("\n", " "),
            }
            if not sources:
                out["problems"].append(f"{action}: nothing retrieved for this skill")
            if foreign:
                out["problems"].append(f"{action}: {foreign} cited passage(s) from another course")
            if action == "explain" and citations_in_text == 0:
                out["problems"].append("explain: the answer carries no [n] citation")
            turns.append(rec)
        out["turns"] = turns
        # assessments: the rotation as the session screen would present it
        grader = Grader(db, gw)
        attempts: list[dict[str, Any]] = []
        for _ in range(3):
            a = await grader.next_item(world.learner_id, node.id)
            if a is None:
                break
            if a.kind == "mcq":
                answer = str(a.item_json["answer"])
            elif a.kind == "cloze":
                answer = str(a.item_json["answers"][0])
            else:
                answer = explain_back_answer(obj.goal if obj else node.title, node.title)
            t0 = time.perf_counter()
            try:
                r = await grader.grade(
                    AttemptRequest(
                        session_id=s.id,
                        assessment_id=a.id,
                        answer=answer,
                        confidence_pre=4,
                        latency_ms=5000,
                    )
                )
            except Exception as e:  # noqa: BLE001
                out["problems"].append(f"grade {a.kind}: {type(e).__name__}: {str(e)[:200]}")
                break
            attempts.append(
                {
                    "kind": a.kind,
                    "grader_level": r.grader_level,
                    "score": r.score,
                    "correct": r.correct,
                    "latency_s": round(time.perf_counter() - t0, 2),
                    "criteria": [(c.criterion[:60], c.passed) for c in r.criterion_results],
                    "feedback_head": r.feedback[:160].replace("\n", " "),
                }
            )
            if a.kind == "mcq" and not r.correct:
                out["problems"].append("mcq: the key answer was graded wrong")
        out["attempts"] = attempts
        if not attempts:
            out["problems"].append("no assessment item offered for this skill")
        out["mastery"] = round(await competency.mastery(db, world.learner_id, node.id), 3)
        due = await memory.due_items(db, world.learner_id, now=datetime.now(UTC), cap=50)
        out["due_items_total"] = len(due)
        await ksession.end(db, s.id, energy_after=3, self_report=4)
        n_evidence = int(
            (
                await db.execute(
                    select(func.count(models.CompetencyEvidence.id)).where(
                        models.CompetencyEvidence.learner_id == world.learner_id,
                        models.CompetencyEvidence.skill_id == node.id,
                    )
                )
            ).scalar_one()
        )
        out["evidence_rows"] = n_evidence
        if attempts and n_evidence == 0:
            out["problems"].append("attempts graded but no competency evidence written")
    return out


async def run(args: argparse.Namespace) -> dict[str, Any]:
    world = await open_snapshot_world()
    report: dict[str, Any] = {
        "course": args.course,
        "snapshot": str(SNAPSHOT),
        "at": datetime.now(UTC).isoformat(),
    }
    try:
        async with world.session_factory() as db:
            drafts = [
                d
                for d in await curriculum.list_drafts(db, world.learner_id)
                if d.course == args.course and d.status == "draft"
            ]
            published = []
            for d in drafts:
                try:
                    rep = await curriculum.publish_draft(db, world.learner_id, d.id)
                    published.append(
                        {
                            "section": d.section,
                            "skills": rep.skills,
                            "objects": rep.learning_objects,
                            "assessments": rep.assessments,
                            "edges": rep.edges,
                        }
                    )
                except ValueError as e:
                    published.append({"section": d.section, "refused": str(e)[:300]})
            report["published"] = published
            await preferences.set_pref(db, world.learner_id, "goal.course", args.course)
            await db.commit()
            nodes = (
                (
                    await db.execute(
                        select(models.SkillNode).where(models.SkillNode.course == args.course)
                    )
                )
                .scalars()
                .all()
            )
            report["course_skills"] = len(nodes)
            objects = {
                o.skill_id: o
                for o in (
                    await db.execute(
                        select(models.LearningObject)
                        .where(models.LearningObject.skill_id.in_([n.id for n in nodes]))
                        .order_by(models.LearningObject.version)
                    )
                ).scalars()
            }
        skills: list[dict[str, Any]] = []
        for _ in range(args.sessions):
            async with world.session_factory() as db:
                node = await skill_graph.next_skill(db, world.learner_id)
            if node is None or node.course != args.course:
                skills.append(
                    {"problems": [f"next_skill left the course: {node.slug if node else None}"]}
                )
                break
            print(f"- rehearsing {node.title!r} …", flush=True)
            skills.append(await rehearse_skill(world, node, objects.get(node.id)))
        report["skills"] = skills
        lat = [t["latency_s"] for s in skills for t in s.get("turns", [])]
        report["turn_latency_s"] = (
            {"median": round(statistics.median(lat), 2), "max": max(lat)} if lat else None
        )
        report["problems"] = [
            f"{s.get('skill')}: {p}" for s in skills for p in s.get("problems", [])
        ]
    finally:
        await world.close()
    return report


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--course", required=True)
    ap.add_argument("--sessions", type=int, default=3, help="how many sessions to rehearse")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    rep = asyncio.run(run(args))
    safe = re.sub(r"[^a-z0-9]+", "-", args.course.lower()).strip("-")[:40]
    path = results_dir() / f"rehearse_{safe}.json"
    path.write_text(json.dumps(rep, indent=2, default=str))
    if args.json:
        print(json.dumps(rep, indent=2, default=str))
        return 0
    print(f"\n{rep['course']} — snapshot {rep['snapshot']} (live DB untouched)")
    for p in rep["published"]:
        if "refused" in p:
            print(f"  publish {p['section']}: refused — {p['refused']}")
        else:
            print(
                f"  published {p['section']}: {p['skills']} skills, {p['objects']} objects, "
                f"{p['assessments']} assessments, {p['edges']} edges"
            )
    print(f"  {rep['course_skills']} skills in the course after publishing")
    for s in rep["skills"]:
        if "title" not in s:
            print(f"  ! {s['problems']}")
            continue
        print(
            f"\n  {s['title']}: mastery {s['mastery']}, {s['evidence_rows']} evidence rows, "
            f"{s['due_items_total']} due items"
        )
        for t in s["turns"]:
            print(
                f"    {t['action']:7} {t['latency_s']:5.1f}s {t['retrieved']} retrieved / {t['cited']} cited "
                f"({t['cited_outside_course']} outside course), {t['citation_marks_in_text']} [n] marks, "
                f"model {t['model']} ({t['outcome']})"
            )
            print(f"            {t['answer_head'][:150]}")
        for a in s["attempts"]:
            print(
                f"    {a['kind']:12} {a['grader_level']:14} score {a['score']:.2f} correct={a['correct']} "
                f"{a['latency_s']:.1f}s — {a['feedback_head'][:100]}"
            )
        for p in s["problems"]:
            print(f"    ! {p}")
    if rep["turn_latency_s"]:
        print(
            f"\n  turn latency median {rep['turn_latency_s']['median']} s, max {rep['turn_latency_s']['max']} s"
        )
    print(f"  {len(rep['problems'])} problem(s); report: {path}")
    return 0 if not rep["problems"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
