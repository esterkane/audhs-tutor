"""experiments slice: templates, balanced matched-node assignment, outcomes from events, results
as hypotheses, session-unit arms, disclosure on SessionOut and turn meta."""

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.db.events import EventWriter, Verb
from app.kernel import experiments, memory
from app.kernel import session as ksession
from app.kernel.seed import load_seed
from app.kernel.skill_graph import all_nodes
from app.models_ai import registry
from app.schemas.common import ActivityType, Domain, Mode, ObjectType
from tests.test_orchestrator import SEED


async def test_template_lifecycle_and_balanced_node_assignment(
    db: AsyncSession, learner: models.LearnerProfile
) -> None:
    exp = await experiments.from_template(db, learner.id, "socratic-vs-explicit")
    assert exp.status == "draft" and exp.unit_type == "node" and exp.metric == "delayed_recall"
    arms = await experiments.arms_of(db, exp.id)
    assert [a.name for a in arms] == ["explicit", "socratic"]
    assert await experiments.arm_for_node(db, learner.id, "n1") is None  # not running yet
    await experiments.start(db, learner.id, exp.id)
    picks = [
        (await experiments.arm_for_node(db, learner.id, f"node-{i}"))[1].name  # type: ignore[index]
        for i in range(6)
    ]
    assert picks.count("explicit") == 3 and picks.count("socratic") == 3  # balanced
    again = await experiments.arm_for_node(db, learner.id, "node-0")
    assert again and again[1].name == picks[0]  # sticky per node
    assigned = [
        e
        for e in (await db.execute(select(models.LearningEvent))).scalars()
        if e.verb == "assigned"
    ]
    assert len(assigned) == 6 and assigned[0].context_json["experiment_id"] == exp.id
    second = await experiments.from_template(db, learner.id, "worked-example-vs-problem-first")
    try:
        await experiments.start(db, learner.id, second.id)
        raise AssertionError("two node-unit experiments must not run at once")
    except ValueError:
        pass
    await experiments.stop(db, learner.id, exp.id)
    assert (await experiments.get(db, learner.id, exp.id)).status == "done"
    assert await experiments.arm_for_node(db, learner.id, "node-9") is None


async def test_outcomes_are_read_from_events_per_arm(
    db: AsyncSession, learner: models.LearnerProfile
) -> None:
    await load_seed(db, SEED)
    nodes = await all_nodes(db, "ai_ml")
    exp = await experiments.from_template(db, learner.id, "socratic-vs-explicit")
    await experiments.start(db, learner.id, exp.id)
    s = await ksession.start(db, learner.id, mode=Mode.STEADY, energy=3)
    ev = EventWriter(
        db, ksession.event_context(s, domain=Domain.AI_ML, activity=ActivityType.RETRIEVAL)
    )
    arm_of: dict[str, str] = {}
    for node in nodes[:4]:
        pair = await experiments.arm_for_node(db, learner.id, node.id, session=s)
        assert pair
        arm_of[node.id] = pair[1].name
        socratic = arm_of[node.id] == "socratic"
        for i in range(3):
            # socratic nodes: better delayed recall in this synthetic history
            await ev.emit(
                Verb.REVIEWED,
                ObjectType.ITEM,
                f"it-{node.id}-{i}",
                result={
                    "rating": 4 if socratic else 2,
                    "latency_ms": 900,
                    "days_since_learned": 2.0
                    if i < 2
                    else 0.0,  # the last one is same-day: ignored
                },
                context={"item_type": "cloze", "node_id": node.id},
            )
            await ev.emit(
                Verb.ATTEMPTED,
                ObjectType.ITEM,
                f"at-{node.id}-{i}",
                result={
                    "correct": socratic or i == 0,
                    "confidence_pre": 3,
                    "latency_ms": 500,
                    "hint_count": 0,
                    "answer_len": 4,
                },
                context={"item_type": "mcq", "node_id": node.id},
            )
    res = await experiments.results(db, learner.id, exp.id, record=True)
    recall = next(m for m in res.metrics if m.metric == "delayed_recall")
    by_name = {a.name: a for a in recall.arms}
    assert by_name["socratic"].mean == 1.0 and by_name["explicit"].mean is not None
    assert by_name["explicit"].mean == 0.0 and by_name["socratic"].n == 4
    assert recall.difference and recall.difference > 0 and "socratic" in recall.reading
    error = next(m for m in res.metrics if m.metric == "error_rate")
    assert error.lower_is_better and {a.name: a.mean for a in error.arms}["socratic"] == 0.0
    transfer = next(m for m in res.metrics if m.metric == "transfer")
    assert transfer.reading == "Not enough data yet for this metric."
    measured = [
        e
        for e in (await db.execute(select(models.LearningEvent))).scalars()
        if e.verb == "measured"
    ]
    assert measured and measured[0].result_json["metric"] in experiments.METRICS
    obs = (await db.execute(select(models.ExperimentObservation))).scalars().all()
    assert len(obs) >= 4 and res.assignments == {"explicit": 2, "socratic": 2}


async def test_session_unit_arm_applies_socratic_and_is_disclosed(client: AsyncClient) -> None:
    created = await client.post(
        "/api/experiments/from-template", json={"template": "short-vs-long-blocks"}
    )
    assert created.status_code == 201
    exp = created.json()
    # switch to a session-unit socratic experiment by hand
    made = await client.post(
        "/api/experiments",
        json={
            "name": "S vs E per session",
            "hypothesis": "h",
            "metric": "completion",
            "unit_type": "session",
            "arms": [
                {"name": "explicit", "config": {"socratic": False}},
                {"name": "socratic", "config": {"socratic": True}},
            ],
        },
    )
    assert made.status_code == 201
    started = await client.post(f"/api/experiments/{made.json()['id']}/start")
    assert started.status_code == 200 and started.json()["status"] == "running"
    clash = await client.post(f"/api/experiments/{exp['id']}/start")
    assert clash.status_code == 400  # one running session-unit experiment at a time
    names = set()
    for _ in range(4):
        s = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
        assert s["experiment"] and s["experiment"]["unit_type"] == "session"
        names.add(s["experiment"]["arm"])
        assert s["socratic"] == (s["experiment"]["arm"] == "socratic")
        await client.post(
            f"/api/sessions/{s['id']}/end", json={"energy_after": 3, "self_report": 3}
        )
    assert names == {"explicit", "socratic"}
    results = (await client.get(f"/api/experiments/{made.json()['id']}/results")).json()
    assert results["primary_metric"] == "completion" and len(results["units"]) == 4
    listing = (await client.get("/api/experiments")).json()
    assert {t["id"] for t in listing["templates"]} >= {
        "socratic-vs-explicit"
    } and "delayed_recall" in listing["metrics"]
    bad = await client.post(
        "/api/experiments",
        json={"name": "x", "metric": "nope", "arms": [{"name": "a"}, {"name": "b"}]},
    )
    assert bad.status_code == 400
    assert (await client.post("/api/experiments/nope/start")).status_code == 404


async def test_node_unit_arm_overrides_turn_style(client: AsyncClient, db: AsyncSession) -> None:
    await load_seed(db, SEED)
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "nomic-embed-text"})
    exp = (
        await client.post(
            "/api/experiments/from-template", json={"template": "socratic-vs-explicit"}
        )
    ).json()
    await client.post(f"/api/experiments/{exp['id']}/start")
    s = (
        await client.post("/api/sessions", json={"mode": "steady", "energy": 3, "socratic": False})
    ).json()
    assert s["experiment"]["unit_type"] == "node" and s["experiment"]["arm"] is None
    node = (await all_nodes(db, "ai_ml"))[0]
    turn = await client.post(
        "/api/tutor/turn",
        json={
            "session_id": s["id"],
            "skill_id": node.id,
            "text": "explain this",
            "action": "explain",
        },
    )
    assert turn.status_code == 200, turn.text
    row = await db.get(models.Session, s["id"])
    assert row
    pair = await experiments.arm_for_node(db, row.learner_id, node.id)
    assert pair is not None
    explained = [
        e
        for e in (await db.execute(select(models.LearningEvent))).scalars()
        if e.verb == "explained"
    ]
    assert explained and explained[-1].experiment_arm == pair[1].id
    trace = (await db.execute(select(models.TutorTrace))).scalars().all()[-1]
    assert trace is not None


async def test_voluntary_continuation_from_session_lengths(
    db: AsyncSession, learner: models.LearnerProfile
) -> None:
    exp = await experiments.create(
        db,
        learner.id,
        name="len",
        hypothesis="",
        metric="voluntary_continuation",
        unit_type="session",
        arms=[{"name": "a", "config": {}}, {"name": "b", "config": {}}],
    )
    await experiments.start(db, learner.id, exp.id)
    for i in range(4):
        s = await ksession.start(
            db, learner.id, mode=Mode.STEADY, energy=3, planned_blocks=["retrieval"]
        )
        s.planned_blocks_json = [{"type": "retrieval", "planned_min": 10}]
        await experiments.arm_for_session(db, learner.id, s)
        s.started_at = (datetime.now(UTC) - timedelta(minutes=30 if i % 2 else 5)).isoformat(
            timespec="seconds"
        )
        await db.commit()
        await ksession.end(db, s.id, energy_after=3, self_report=3)
    res = await experiments.results(db, learner.id, exp.id)
    vc = next(m for m in res.metrics if m.metric == "voluntary_continuation")
    assert sum(a.n for a in vc.arms) == 4 and any(
        a.mean == 1.0 or a.mean == 0.0 or a.mean == 0.5 for a in vc.arms
    )
    assert memory.review_cap("steady", 3) > 0  # unrelated guard that the kernel import is live


async def test_assignment_is_unique_per_unit_and_window_keeps_delayed_reviews(
    db: AsyncSession, learner: models.LearnerProfile
) -> None:
    from sqlalchemy.exc import IntegrityError

    exp = await experiments.from_template(db, learner.id, "socratic-vs-explicit")
    await experiments.start(db, learner.id, exp.id)
    exp_id, learner_id = exp.id, learner.id
    arm_id = (await experiments.assign(db, learner_id, exp, unit_id="node-x")).id
    db.add(
        models.ExperimentAssignment(
            learner_id=learner_id,
            experiment_id=exp_id,
            arm_id=arm_id,
            unit_type="node",
            unit_id="node-x",
        )
    )
    try:
        await db.commit()
        raise AssertionError("duplicate assignment must be rejected")
    except IntegrityError:
        await db.rollback()
    exp = await experiments.get(db, learner_id, exp_id)
    assert (await experiments.assign(db, learner_id, exp, unit_id="node-x")).id == arm_id
    await experiments.stop(db, learner_id, exp_id)
    s = await ksession.start(db, learner_id, mode=Mode.STEADY, energy=3)
    ev = EventWriter(
        db, ksession.event_context(s, domain=Domain.AI_ML, activity=ActivityType.RETRIEVAL)
    )
    await ev.emit(
        Verb.REVIEWED,
        ObjectType.ITEM,
        "late",
        result={"rating": 4, "latency_ms": 500, "days_since_learned": 3.0},
        context={"item_type": "cloze", "node_id": "node-x"},
    )
    res = await experiments.results(db, learner_id, exp_id)
    recall = next(m for m in res.metrics if m.metric == "delayed_recall")
    assert sum(a.n for a in recall.arms) == 1  # a review after Stop still counts as the outcome
