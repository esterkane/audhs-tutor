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
    # analysis v2: the assigned unit is the observation — 2 nodes with 2 delayed reviews each
    assert by_name["explicit"].mean == 0.0 and by_name["socratic"].n_units == 2
    assert by_name["socratic"].n_events == 4 and by_name["socratic"].n == 2
    assert recall.ci95 is not None and recall.ci95[0] < recall.ci95[1]  # never zero-width
    assert "not evidence for either arm" in recall.reading  # 2 units per arm: no "supported"
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
        # v2 counts *active* time (ended blocks' measured minutes), not the open-tab duration:
        # sessions 1 and 3 worked 30 min on a 10-min plan, sessions 0 and 2 only 5
        await EventWriter(db, ksession.event_context(s, activity=ActivityType.RETRIEVAL)).emit(
            Verb.BLOCK_ENDED,
            ObjectType.BLOCK,
            f"{s.id}:0",
            result={
                "actual_min": 30 if i % 2 else 5,
                "switched_early": False,
                "reason": "finished",
            },
            context={"block_type": "retrieval", "planned_min": 10, "node_ids": []},
        )
        await ksession.end(db, s.id, energy_after=3, self_report=3)
    res = await experiments.results(db, learner.id, exp.id)
    vc = next(m for m in res.metrics if m.metric == "voluntary_continuation")
    assert sum(a.n_units for a in vc.arms) == 4 and vc.available
    assert sorted(v for a in vc.arms for v in a.unit_means) == [0.0, 0.0, 1.0, 1.0]
    assert "Neither direction" in vc.reading
    # an idle session (long open, nothing ended) is not "continuation"
    idle = await ksession.start(
        db, learner.id, mode=Mode.STEADY, energy=3, planned_blocks=["retrieval"]
    )
    idle.planned_blocks_json = [{"type": "retrieval", "planned_min": 10}]
    await experiments.arm_for_session(db, learner.id, idle)
    idle.started_at = (datetime.now(UTC) - timedelta(hours=3)).isoformat(timespec="seconds")
    await db.commit()
    await ksession.end(db, idle.id, energy_after=3, self_report=3)
    res = await experiments.results(db, learner.id, exp.id)
    vc = next(m for m in res.metrics if m.metric == "voluntary_continuation")
    assert sum(a.n_units for a in vc.arms) == 4 and res.units_without_data == 1
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


async def test_v2_duplicate_events_do_not_multiply_units_and_sparse_success_is_not_certainty(
    db: AsyncSession, learner: models.LearnerProfile
) -> None:
    await load_seed(db, SEED)
    nodes = await all_nodes(db, "ai_ml")
    exp = await experiments.from_template(db, learner.id, "socratic-vs-explicit")
    await experiments.start(db, learner.id, exp.id)
    s = await ksession.start(db, learner.id, mode=Mode.STEADY, energy=3)
    ev = EventWriter(db, ksession.event_context(s, activity=ActivityType.RETRIEVAL))
    arms: dict[str, list[str]] = {}
    for node in nodes[:2]:
        pair = await experiments.arm_for_node(db, learner.id, node.id, session=s)
        assert pair
        arms.setdefault(pair[1].name, []).append(node.id)
    # one node per arm; the "socratic" node gets TEN delayed reviews, all Good — still ONE unit
    for arm_name, node_ids in arms.items():
        for k in range(10 if arm_name == "socratic" else 3):
            await ev.emit(
                Verb.REVIEWED,
                ObjectType.ITEM,
                f"it-{node_ids[0]}-{k}",
                result={"rating": 4, "latency_ms": 800, "days_since_learned": 3.0},
                context={"item_type": "cloze", "node_id": node_ids[0]},
            )
    res = await experiments.results(db, learner.id, exp.id)
    recall = next(m for m in res.metrics if m.metric == "delayed_recall")
    for a in recall.arms:
        assert a.n_units == 1 and a.n_events in (3, 10) and a.mean == 1.0
    assert recall.difference == 0.0 and recall.ci95 is not None
    assert recall.ci95[0] < 0 < recall.ci95[1]  # all-success on 1 vs 1 unit: wide, not zero
    assert recall.reading.startswith("No clear difference") and "1+1" in recall.reading
    assert res.analysis_version == "v2" and recall.method == "newcombe_wilson_units"
    # node-unit experiments cannot measure block completion: said so, never a fake number
    completion = next(m for m in res.metrics if m.metric == "completion")
    assert completion.available is False and "not measurable" in completion.reading.lower()


async def test_v2_low_fidelity_units_are_excluded_and_counted(
    db: AsyncSession, learner: models.LearnerProfile
) -> None:
    await load_seed(db, SEED)
    nodes = await all_nodes(db, "ai_ml")
    exp = await experiments.from_template(db, learner.id, "socratic-vs-explicit")
    await experiments.start(db, learner.id, exp.id)
    s = await ksession.start(db, learner.id, mode=Mode.STEADY, energy=3)
    ev = EventWriter(db, ksession.event_context(s, activity=ActivityType.NEW_MATERIAL))
    socratic_nodes: list[str] = []
    for node in nodes[:4]:
        pair = await experiments.arm_for_node(db, learner.id, node.id, session=s)
        assert pair
        if pair[1].name == "socratic":
            socratic_nodes.append(node.id)
        for k in range(2):
            await ev.emit(
                Verb.REVIEWED,
                ObjectType.ITEM,
                f"r-{node.id}-{k}",
                result={"rating": 4, "latency_ms": 800, "days_since_learned": 2.0},
                context={"item_type": "cloze", "node_id": node.id},
            )
    # the first socratic node never actually got Socratic turns (model explained instead)
    bad, good = socratic_nodes[0], socratic_nodes[1]
    for node_id, delivered in ((bad, False), (bad, False), (bad, True), (good, True), (good, True)):
        await ev.emit(
            Verb.EXPLAINED,
            ObjectType.TURN,
            f"t-{node_id}-{delivered}-{id(object())}",
            result={"sentences": 3, "cited_sources": []},
            context={
                "node_id": node_id,
                "representation": "narrative",
                "hint_count": 0,
                "model": "fake",
                "route": "primary",
                "prompt_version": "v1",
                "questioning_style": "socratic",
                "arm_intended": {"socratic": True},
                "arm_delivered": delivered,
            },
        )
    res = await experiments.results(db, learner.id, exp.id)
    assert res.low_fidelity_units == 1 and any("excluded" in c for c in res.caveats)
    recall = next(m for m in res.metrics if m.metric == "delayed_recall")
    by_name = {a.name: a for a in recall.arms}
    assert by_name["socratic"].n_units == 1 and by_name["explicit"].n_units == 2
    assert by_name["socratic"].fidelity == 1.0
    assert "left out" in recall.reading


async def test_v2_outcome_window_after_stop(
    db: AsyncSession, learner: models.LearnerProfile
) -> None:
    await load_seed(db, SEED)
    nodes = await all_nodes(db, "ai_ml")
    exp = await experiments.from_template(db, learner.id, "socratic-vs-explicit")
    await experiments.start(db, learner.id, exp.id)
    s = await ksession.start(db, learner.id, mode=Mode.STEADY, energy=3)
    pair = await experiments.arm_for_node(db, learner.id, nodes[0].id, session=s)
    assert pair
    await experiments.stop(db, learner.id, exp.id)
    ev = EventWriter(db, ksession.event_context(s, activity=ActivityType.RETRIEVAL))
    await ev.emit(
        Verb.REVIEWED,
        ObjectType.ITEM,
        "after-stop",
        result={"rating": 3, "latency_ms": 500, "days_since_learned": 2.0},
        context={"item_type": "cloze", "node_id": nodes[0].id},
    )
    exp_row = await experiments.get(db, learner.id, exp.id)
    units = await experiments.unit_outcomes(db, learner.id, exp_row)
    assert units[nodes[0].id].values["delayed_recall"] == [
        1.0
    ]  # a delayed review after Stop counts
    # …but only inside the documented window: pretend the experiment stopped 31 days ago
    exp_row.ended_at = (
        datetime.now(UTC) - timedelta(days=experiments.OUTCOME_WINDOW_DAYS + 1)
    ).isoformat(timespec="milliseconds")
    await db.commit()
    units = await experiments.unit_outcomes(db, learner.id, exp_row)
    assert units[nodes[0].id].values == {}
    res = await experiments.results(db, learner.id, exp.id)
    assert (
        res.outcome_window_days == experiments.OUTCOME_WINDOW_DAYS and res.units_without_data == 1
    )


def test_v2_interval_functions() -> None:
    lo, hi = experiments.wilson(7, 10)
    assert (round(lo, 3), round(hi, 3)) == (0.397, 0.892)
    assert experiments.wilson(0, 0) == (0.0, 1.0)
    d, (lo, hi) = experiments.newcombe_diff(1, 1, 1, 1) or (0.0, (0.0, 0.0))
    assert d == 0.0 and (round(lo, 3), round(hi, 3)) == (-0.793, 0.793)  # all-success 1v1: wide
    assert experiments.newcombe_diff(0, 0, 1, 1) is None
    assert experiments.welch_diff([1.0], [1.0, 2.0, 3.0]) == (1.0, None)  # n=1: no interval
    assert experiments.welch_diff([2.0, 2.0], [2.0, 2.0]) == (0.0, None)  # no spread: no interval
    d2, ci2 = experiments.welch_diff([1.0, 2.0, 3.0], [4.0, 5.0, 7.0]) or (0.0, None)
    assert ci2 is not None and ci2[0] < d2 < ci2[1] and round(d2, 3) == 3.333
    assert experiments._t95(1.5) == 12.706 and experiments._t95(10.5) == 2.228  # floor, not ceil
    assert experiments._t95(0.5) == 12.706 and experiments._t95(500) == 1.96


def test_v2_fidelity_heuristics() -> None:
    from app.orchestrator.tutor import arm_fidelity, socratic_delivered

    assert socratic_delivered("Which term dominates the softmax? [2]")  # trailing citation ok
    assert socratic_delivered(
        "Think of the keys as labels. Which label matches the query? (a) k1 (b) k2"
    )
    assert not socratic_delivered("Scaling divides the scores by sqrt(d_k). This keeps it soft.")
    explicit = {"socratic": False}
    # an explicit turn that ends with a check question is still a delivered explicit turn
    out = arm_fidelity(
        explicit,
        text="Step 1: scale. What happens if d_k is large?",
        completed=True,
        arm_not_applied=False,
    )
    assert out == {"arm_intended": explicit, "arm_delivered": True}
    soc = {"socratic": True}
    explained = arm_fidelity(
        soc, text="Scaling divides by sqrt(d_k). Done.", completed=True, arm_not_applied=False
    )
    assert explained["arm_delivered"] is False
    partial = arm_fidelity(soc, text="partial…", completed=False, arm_not_applied=False)
    assert "arm_delivered" not in partial  # cancelled stream: no verdict
    rep = {"representation": "worked_example"}
    wrong = arm_fidelity(
        rep, text="…", completed=True, arm_not_applied=False, detected_representation="analogy"
    )
    right = arm_fidelity(
        rep,
        text="…",
        completed=True,
        arm_not_applied=False,
        detected_representation="worked_example",
    )
    assert wrong["arm_delivered"] is False and right["arm_delivered"] is True
    refused = arm_fidelity(rep, text="…", completed=True, arm_not_applied=True)
    assert refused["arm_delivered"] is False and refused["arm_not_applied"] is True
    assert arm_fidelity(None, text="x", completed=True, arm_not_applied=False) == {}


async def test_v2_pre_assignment_reviews_and_transfer_attribution(
    db: AsyncSession, learner: models.LearnerProfile
) -> None:
    await load_seed(db, SEED)
    nodes = await all_nodes(db, "ai_ml")
    exp = await experiments.from_template(db, learner.id, "socratic-vs-explicit")
    await experiments.start(db, learner.id, exp.id)
    s = await ksession.start(db, learner.id, mode=Mode.STEADY, energy=3)
    ev = EventWriter(db, ksession.event_context(s, activity=ActivityType.RETRIEVAL))
    # a review *before* the node was assigned to an arm must not count for that arm
    await ev.emit(
        Verb.REVIEWED,
        ObjectType.ITEM,
        "early",
        result={"rating": 4, "latency_ms": 500, "days_since_learned": 2.0},
        context={"item_type": "cloze", "node_id": nodes[0].id},
    )
    pair = await experiments.arm_for_node(db, learner.id, nodes[0].id, session=s)
    assert pair
    units = await experiments.unit_outcomes(db, learner.id, exp)
    assert units[nodes[0].id].values == {}
    # transfer evidence carries the skill in the result, not in the context
    await ev.emit(
        Verb.EVIDENCED,
        ObjectType.NODE,
        nodes[0].id,
        result={"skill_id": nodes[0].id, "dimension": "transfer", "score": 0.75, "weight": 1.0},
        context={"attempt_id": "a1"},
    )
    units = await experiments.unit_outcomes(db, learner.id, exp)
    assert units[nodes[0].id].values["transfer"] == [0.75]


async def test_v2_three_arms_compare_the_first_two_and_session_units_omit_recall(
    db: AsyncSession, learner: models.LearnerProfile
) -> None:
    exp = await experiments.create(
        db,
        learner.id,
        name="three",
        hypothesis="",
        metric="completion",
        unit_type="session",
        arms=[
            {"name": "a", "config": {}},
            {"name": "b", "config": {}},
            {"name": "c", "config": {}},
        ],
    )
    await experiments.start(db, learner.id, exp.id)
    res = await experiments.results(db, learner.id, exp.id)
    completion = next(m for m in res.metrics if m.metric == "completion")
    assert (
        len(completion.arms) == 3 and completion.reading == "Not enough data yet for this metric."
    )
    recall = next(m for m in res.metrics if m.metric == "delayed_recall")
    assert recall.available is False and "later session" in recall.reading
