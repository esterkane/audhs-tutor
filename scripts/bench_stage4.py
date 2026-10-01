#!/usr/bin/env python3
"""Stage 4 benchmark (docs/ROADMAP.md). Run: make bench s=4
The ROADMAP asks for "one 2-week experiment (Socratic vs explicit on matched nodes) and read the
results". A real run takes two weeks of the owner's sessions; this script runs the *same pipeline*
on an isolated DB (data/bench4.db) with time travel: six matched attention nodes, each taught in
its assigned arm by the real local model, assessed, and reviewed two days later, spread over 14
simulated days — then reads the dashboard the owner would read.
A adaptation cards: pattern → card → Try applies → next session expires it (undone, logged)
B two-week n-of-1 experiment: balanced matched-node assignment, arm-stamped events, results + reading
C energy check-in → re-plan card → apply → undo restores the plan
D domain blocks: vocab deck → language block planned → reviewed in the language block only; movement
  skipped three times → movement_skipped card
E models registry: routing table resolves every task class to a ready model or says none is ready
"""

import asyncio
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from app.db import models  # noqa: E402
from app.db.events import EventWriter, Verb  # noqa: E402
from app.evals.harness import open_world, results_dir  # noqa: E402
from app.kernel import (  # noqa: E402
    adaptation,
    experiments,
    memory,
    planner,
    practice,
    preferences,
    skill_graph,  # noqa: E402
)
from app.kernel import session as ksession  # noqa: E402
from app.models_ai import manage  # noqa: E402
from app.orchestrator.grader import Grader  # noqa: E402
from app.orchestrator.tutor import TutorTurn  # noqa: E402
from app.schemas.common import ActivityType, Domain, Mode, ObjectType  # noqa: E402
from app.schemas.grading import AttemptRequest  # noqa: E402
from app.schemas.tutor import TurnRequest  # noqa: E402

results: dict[str, dict[str, Any]] = {}


def record(key: str, status: str, **data: Any) -> None:
    results[key] = {"status": status, **data}
    print(f"[{status:4}] {key}: {json.dumps(data, default=str)[:900]}", flush=True)


async def check_a(world: Any) -> None:
    async with world.session_factory() as db:
        s1 = await ksession.start(db, world.learner_id, mode=Mode.STEADY, energy=3)
        ev = EventWriter(db, ksession.event_context(s1, activity=ActivityType.NEW_MATERIAL))
        for i in range(8):
            await ev.emit(
                Verb.ATTEMPTED,
                ObjectType.ITEM,
                f"i{i}",
                result={
                    "correct": True,
                    "confidence_pre": 3,
                    "latency_ms": 100,
                    "hint_count": 3,
                    "answer_len": 3,
                },
                context={"item_type": "mcq", "node_id": "n"},
            )
        cards = await adaptation.observe(db, world.learner_id, session=s1)
        card = next((c for c in cards if c.pattern == "hint_heavy"), None)
        if card is None:
            record("A adaptation card lifecycle", "FAIL", cards=[c.pattern for c in cards])
            return
        await adaptation.decide(db, world.learner_id, card.id, "try", session=s1)
        applied = await preferences.get(db, world.learner_id, "tutor.representation_default")
        await ksession.end(db, s1.id, energy_after=3, self_report=3)
        s2 = await ksession.start(db, world.learner_id, mode=Mode.STEADY, energy=3)
        expired = await adaptation.expire_trials(db, world.learner_id, current_session=s2)
        restored = await preferences.get(db, world.learner_id, "tutor.representation_default")
        verbs = [
            e.verb
            for e in (await db.execute(select(models.LearningEvent))).scalars()
            if e.verb in ("proposed", "decided", "adapted", "undone")
        ]
        await ksession.end(db, s2.id, energy_after=3, self_report=3)
        ok = (
            applied == "worked_example"
            and expired == 1
            and restored == ""
            and set(verbs) == {"proposed", "decided", "adapted", "undone"}
        )
        record(
            "A adaptation card lifecycle",
            "PASS" if ok else "FAIL",
            card=card.what,
            why=card.why,
            applied=applied,
            expired=expired,
            restored=restored,
            events=sorted(set(verbs)),
        )


async def check_b(world: Any) -> None:
    async with world.session_factory() as db:
        exp = await experiments.from_template(db, world.learner_id, "socratic-vs-explicit")
        await experiments.start(db, world.learner_id, exp.id)
        nodes = [n for n in await skill_graph.all_nodes(db, "ai_ml")][:6]
        day0 = datetime.now(UTC) - timedelta(days=14)
        per_node: list[dict[str, Any]] = []
        gw = world.gateway(db)
        for i, node in enumerate(nodes):
            day = day0 + timedelta(days=2 * i)
            s = await ksession.start(db, world.learner_id, mode=Mode.STEADY, energy=3)
            s.started_at = day.isoformat(timespec="seconds")
            await db.commit()
            turn = TutorTurn(db, gw, world.repo)
            meta = done = None
            async for kind, data in turn.run(
                TurnRequest(
                    session_id=s.id,
                    text=f"Explain {node.title}.",
                    skill_id=node.id,
                    action="explain",
                )
            ):
                if kind == "meta":
                    meta = data
                elif kind == "done":
                    done = data
            assert meta and done
            grader = Grader(db, gw)
            correct = None
            item = await grader.next_item(world.learner_id, node.id)
            if item is not None:
                if item.kind == "mcq":
                    answer = str(item.item_json["answer"])
                elif item.kind == "cloze":
                    answer = item.item_json["answers"][0]
                else:
                    answer = "the variance grows with d_k, dividing by sqrt restores unit variance"
                res = await grader.grade(
                    AttemptRequest(
                        session_id=s.id,
                        assessment_id=item.id,
                        answer=answer,
                        confidence_pre=3,
                        latency_ms=4000,
                    ),
                    now=day,
                )
                correct = res.correct
            await ksession.end(db, s.id, energy_after=3, self_report=3)
            # two days later: the simulated learner reviews; recall depends on the explanation quality
            # under that arm (cited a source and stayed short → remembered)
            cited = any(src.get("cited") for src in done.get("sources", []))
            short = int(done.get("sentences", 99)) <= 6
            rating = 4 if (cited and short) else (3 if cited or short else 2)
            later = day + timedelta(days=2)
            items = (
                (
                    await db.execute(
                        select(models.ReviewItem).where(
                            models.ReviewItem.learner_id == world.learner_id,
                            models.ReviewItem.skill_id == node.id,
                        )
                    )
                )
                .scalars()
                .all()
            )
            ev = EventWriter(db, ksession.event_context(s, activity=ActivityType.RETRIEVAL))
            for it in items:  # the learner sits the node's cards two days later, due or not
                await memory.review(
                    db, world.learner_id, it.id, rating, now=later, latency_ms=2500, events=ev
                )
            per_node.append(
                {
                    "node": node.slug,
                    "arm": meta.get("questioning_style"),
                    "cited": cited,
                    "sentences": done.get("sentences"),
                    "correct": correct,
                    "review_rating": rating,
                }
            )
        arm_events = (
            (
                await db.execute(
                    select(models.LearningEvent).where(
                        models.LearningEvent.experiment_arm.is_not(None)
                    )
                )
            )
            .scalars()
            .all()
        )
        await experiments.stop(db, world.learner_id, exp.id)
        res = await experiments.results(db, world.learner_id, exp.id, record=True)
        recall = next(m for m in res.metrics if m.metric == "delayed_recall")
        arms = {a.name: {"n": a.n, "mean": a.mean} for a in recall.arms}
        balanced = set(res.assignments.values()) == {3}
        ok = (
            balanced
            and all(a["n"] >= 3 for a in arms.values())
            and bool(recall.reading)
            and len(arm_events) >= 12
        )
        record(
            "B two-week Socratic vs explicit on matched nodes (simulated)",
            "PASS" if ok else "FAIL",
            assignments=res.assignments,
            delayed_recall=arms,
            difference=recall.difference,
            ci95=recall.ci95,
            reading=recall.reading,
            other_metrics={
                m.metric: {a.name: a.mean for a in m.arms}
                for m in res.metrics
                if m.metric != "delayed_recall"
            },
            arm_stamped_events=len(arm_events),
            per_node=per_node,
            simulated_days=14,
        )


async def check_c(world: Any) -> None:
    async with world.session_factory() as db:
        s = await ksession.start(
            db, world.learner_id, mode=Mode.STEADY, energy=4, planned_blocks=["retrieval"]
        )
        plan = planner.plan_session(
            planner.PlanInput(
                mode="steady", energy=4, due_reviews=3, next_skill_id="k", review_node_ids=["a"]
            )
        )
        s.planned_blocks_json = [b.model_dump() for b in plan.blocks]
        await db.commit()
        idx = plan.types().index("new_material")
        new = planner.replan(plan, from_index=idx, energy=1)
        card = await adaptation.propose(
            db,
            world.learner_id,
            what="Re-plan",
            why="energy 1",
            pref="session.plan",
            value={"blocks": [b.model_dump() for b in new.blocks], "energy": 1},
            origin="planner",
            session=s,
        )
        await adaptation.decide(db, world.learner_id, card.id, "try", session=s)
        await db.refresh(s)
        applied = s.planned_blocks_json == [b.model_dump() for b in new.blocks]
        await adaptation.undo(db, world.learner_id, card.id, session=s)
        await db.refresh(s)
        restored = s.planned_blocks_json == [b.model_dump() for b in plan.blocks]
        await ksession.end(db, s.id, energy_after=1, self_report=2)
        record(
            "C energy check-in re-plan card apply + undo",
            "PASS" if applied and restored else "FAIL",
            before_min=plan.total_min,
            after_min=new.total_min,
            applied=applied,
            restored=restored,
        )


async def check_d(world: Any) -> None:
    async with world.session_factory() as db:
        past = datetime.now(UTC) - timedelta(days=1)
        for w, t in (("der Hund", "the dog"), ("die Katze", "the cat"), ("das Haus", "the house")):
            await practice.add_vocab(
                db, world.learner_id, lang="de", word=w, translation=t, now=past
            )
        await preferences.set_pref(db, world.learner_id, "planner.language", True)
        due_lang = await practice.language_due(db, world.learner_id)
        ai_due = await memory.due_items(
            db, world.learner_id, cap=100, exclude_domains=("language",)
        )
        ai_has_vocab = any(i.item_type == "vocab" for i, _ in ai_due)
        plan = planner.plan_session(
            planner.PlanInput(
                mode="steady",
                energy=4,
                due_reviews=len(ai_due),
                next_skill_id="k",
                language_due=due_lang,
            )
        )
        block = next((b for b in plan.blocks if b.type == "domain_switch"), None)
        s = await ksession.start(db, world.learner_id, mode=Mode.STEADY, energy=4)
        for it, _ in await memory.due_items(db, world.learner_id, cap=50, domain="language"):
            await memory.review(db, world.learner_id, it.id, 3, latency_ms=1500)
        left = await practice.language_due(db, world.learner_id)
        ev = EventWriter(
            db, ksession.event_context(s, domain=Domain.MOVEMENT, activity=ActivityType.MOVEMENT)
        )
        for _ in range(3):
            await ev.emit(
                Verb.BLOCK_ENDED,
                ObjectType.BLOCK,
                "mv",
                result={"actual_min": 0, "switched_early": True, "reason": "skipped"},
                context={"block_type": "movement_primer", "planned_min": 4, "node_ids": []},
            )
        logged = await practice.log_practice(
            db,
            world.learner_id,
            domain="guitar",
            activity="chord changes",
            duration_min=8,
            self_rating=4,
            session=s,
        )
        cards = await adaptation.observe(db, world.learner_id, session=s)
        await ksession.end(db, s.id, energy_after=3, self_report=3)
        ok = (
            due_lang == 3
            and not ai_has_vocab
            and block is not None
            and block.domain == "language"
            and left == 0
            and any(c.pattern == "movement_skipped" for c in cards)
            and bool(logged["event_id"])
        )
        record(
            "D domain blocks: vocab in the language block only, practiced, movement_skipped card",
            "PASS" if ok else "FAIL",
            vocab_due=due_lang,
            ai_review_has_vocab=ai_has_vocab,
            domain_block=block.model_dump() if block else None,
            vocab_left_after_block=left,
            cards=[c.pattern for c in cards],
        )


async def check_e(world: Any) -> None:
    async with world.session_factory() as db:
        table = await manage.routing_table(db, world.settings, world.learner_id)
        resolved = {r["task"]: r["resolved"] for r in table}
        ok = (
            len(table) == len(resolved)
            and resolved.get("chat") is not None
            and resolved.get("embed") is not None
        )
        record(
            "E models registry routing table",
            "PASS" if ok else "FAIL",
            tasks=len(table),
            resolved={k: v for k, v in resolved.items() if v},
            unresolved=[k for k, v in resolved.items() if not v],
        )


async def main() -> int:
    world = await open_world("bench4.db", fresh=True)
    try:
        for name, fn in (
            ("A", check_a),
            ("B", check_b),
            ("C", check_c),
            ("D", check_d),
            ("E", check_e),
        ):
            try:
                await fn(world)
            except Exception as e:
                record(f"{name} (crashed)", "FAIL", error=f"{type(e).__name__}: {e}")
    finally:
        await world.close()
    out = results_dir() / "bench_stage4.json"
    out.write_text(json.dumps(results, indent=2, default=str))
    failed = [k for k, v in results.items() if v["status"] == "FAIL"]
    print(
        "\nSTAGE 4 BENCHMARK:",
        "FAIL" if failed else "PASS",
        f"({len(results)} checks, {len(failed)} failed)",
    )
    print(f"written: {out}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
