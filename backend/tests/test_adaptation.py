"""adaptation-proposals slice: rules over the event log, cards, decisions, undo, trial expiry."""

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.db.events import EventWriter, Verb
from app.kernel import adaptation, memory, preferences
from app.kernel import session as ksession
from app.kernel.seed import load_seed
from app.kernel.skill_graph import get_node_by_slug
from app.schemas.common import ActivityType, Domain, Mode, ObjectType
from tests.test_orchestrator import SEED


async def _events(db: AsyncSession, s: models.Session) -> EventWriter:
    return EventWriter(
        db, ksession.event_context(s, domain=Domain.AI_ML, activity=ActivityType.NEW_MATERIAL)
    )


async def _emit_attempts(db: AsyncSession, s: models.Session, n: int, hint_count: int) -> None:
    ev = await _events(db, s)
    for i in range(n):
        await ev.emit(
            Verb.ATTEMPTED,
            ObjectType.ITEM,
            f"item-{i}",
            result={
                "correct": True,
                "confidence_pre": 3,
                "latency_ms": 100,
                "hint_count": hint_count,
                "answer_len": 5,
            },
            context={"item_type": "mcq", "node_id": "n"},
        )


async def test_no_cards_without_evidence(db: AsyncSession, learner: models.LearnerProfile) -> None:
    assert await adaptation.observe(db, learner.id) == []


async def test_hint_heavy_card_try_expires_next_session(
    db: AsyncSession, learner: models.LearnerProfile
) -> None:
    s1 = await ksession.start(db, learner.id, mode=Mode.STEADY, energy=3)
    await _emit_attempts(db, s1, 8, hint_count=3)
    cards = await adaptation.observe(db, learner.id, session=s1)
    assert [c.pattern for c in cards] == ["hint_heavy"]
    card = cards[0]
    assert card.apply_json == {"pref": "tutor.representation_default", "value": "worked_example"}
    assert "3.0 hints per attempt" in card.why and card.evidence_json["attempts"] == 8
    # observing again does not duplicate an open card
    assert len(await adaptation.observe(db, learner.id, session=s1)) == 1
    # try = this session only
    await adaptation.decide(db, learner.id, card.id, "try", session=s1)
    assert await preferences.get(db, learner.id, "tutor.representation_default") == "worked_example"
    pref = (
        await db.execute(
            select(models.LearnerPreference).where(
                models.LearnerPreference.key == "tutor.representation_default"
            )
        )
    ).scalar_one()
    assert pref.origin == "proposed_accepted"
    verbs = [
        e.verb
        for e in (
            await db.execute(select(models.LearningEvent).order_by(models.LearningEvent.ts))
        ).scalars()
    ]
    assert verbs.count("proposed") == 1 and "adapted" in verbs and "decided" in verbs
    await ksession.end(db, s1.id, energy_after=3, self_report=3)
    s2 = await ksession.start(db, learner.id, mode=Mode.STEADY, energy=3)
    assert await adaptation.expire_trials(db, learner.id, current_session=s2) == 1
    assert await preferences.get(db, learner.id, "tutor.representation_default") == ""
    undone = [
        e for e in (await db.execute(select(models.LearningEvent))).scalars() if e.verb == "undone"
    ]
    assert undone and undone[0].context_json["why"] == "trial session ended"
    # the pattern is still present: a new card may be proposed again after the trial
    assert [c.pattern for c in await adaptation.observe(db, learner.id, session=s2)] == [
        "hint_heavy"
    ]


async def test_default_then_undo_and_never_blocks(
    db: AsyncSession, learner: models.LearnerProfile
) -> None:
    s = await ksession.start(db, learner.id, mode=Mode.STEADY, energy=3)
    await _emit_attempts(db, s, 6, hint_count=3)
    card = (await adaptation.observe(db, learner.id, session=s))[0]
    await adaptation.decide(db, learner.id, card.id, "default", session=s)
    assert await preferences.get(db, learner.id, "tutor.representation_default") == "worked_example"
    assert await adaptation.observe(db, learner.id, session=s) == []  # in effect → not re-proposed
    hist = await adaptation.history(db, learner.id)
    assert hist[0].decision == "default" and hist[0].in_effect
    await adaptation.undo(db, learner.id, card.id, session=s)
    assert await preferences.get(db, learner.id, "tutor.representation_default") == ""
    assert not (await adaptation.history(db, learner.id))[0].in_effect
    # after undo the pattern can come back; 'never' silences it for good
    card2 = (await adaptation.observe(db, learner.id, session=s))[0]
    await adaptation.decide(db, learner.id, card2.id, "never", session=s)
    assert await adaptation.observe(db, learner.id, session=s) == []
    assert await preferences.get(db, learner.id, "tutor.representation_default") == ""


async def test_no_blocks_for_fourteen_days(
    db: AsyncSession, learner: models.LearnerProfile
) -> None:
    s = await ksession.start(db, learner.id, mode=Mode.STEADY, energy=3)
    await _emit_attempts(db, s, 6, hint_count=3)
    card = (await adaptation.observe(db, learner.id, session=s))[0]
    d = await adaptation.decide(db, learner.id, card.id, "no", session=s)
    assert await adaptation.observe(db, learner.id, session=s) == []
    d.decided_at = (datetime.now(UTC) - timedelta(days=15)).isoformat(timespec="seconds")
    await db.commit()
    assert [c.pattern for c in await adaptation.observe(db, learner.id, session=s)] == [
        "hint_heavy"
    ]


async def test_early_exit_low_energy_and_backlog_rules(
    db: AsyncSession, learner: models.LearnerProfile
) -> None:
    await load_seed(db, SEED)
    node = await get_node_by_slug(db, "attn-scaled")
    assert node
    for energy in (1, 2, 1, 3):
        s = await ksession.start(db, learner.id, mode=Mode.STEADY, energy=energy)
        ev = await _events(db, s)
        for _ in range(1):
            await ev.emit(
                Verb.BLOCK_ENDED,
                ObjectType.BLOCK,
                "b",
                result={"actual_min": 4, "switched_early": True, "reason": "too hard"},
                context={"block_type": "new_material", "planned_min": 20, "node_ids": []},
            )
        await ksession.end(db, s.id, energy_after=2, self_report=2)
    now = datetime.now(UTC)
    for i in range(16):
        await memory.ensure_item(
            db,
            learner.id,
            node.id,
            "cloze",
            {"ref": f"c{i}", "text": "x"},
            now=now - timedelta(days=3),
        )
    cards = await adaptation.observe(db, learner.id)
    patterns = {c.pattern: c for c in cards}
    assert {"early_exit", "low_energy_sessions", "review_backlog"} <= set(patterns)
    assert patterns["early_exit"].apply_json == {"pref": "planner.new_material_min", "value": 15}
    assert patterns["low_energy_sessions"].apply_json["value"] == "low_capacity"
    assert patterns["review_backlog"].apply_json["value"] == 15
    assert patterns["review_backlog"].evidence_json["due"] >= 16


async def test_planner_proposal_and_routes(client: AsyncClient, db: AsyncSession) -> None:
    started = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    learner_id = (await client.get("/api/learner/me")).json()["id"]
    s = await db.get(models.Session, started["id"])
    assert s
    card = await adaptation.propose(
        db,
        learner_id,
        what="Shorten the rest of this session",
        why="Energy dropped to 1.",
        pref="planner.new_material_min",
        value=8,
        session=s,
    )
    same = await adaptation.propose(
        db, learner_id, what="x", why="y", pref="planner.new_material_min", value=8, session=s
    )
    assert same.id == card.id  # one open card per pattern
    listed = (await client.get("/api/adaptations")).json()["proposals"]
    assert [p["id"] for p in listed] == [card.id] and listed[0]["origin"] == "planner"
    decided = await client.post(
        f"/api/adaptations/{card.id}/decide", json={"decision": "try", "session_id": s.id}
    )
    assert decided.status_code == 200
    entry = decided.json()["entries"][0]
    assert entry["in_effect"] and entry["trial"] and entry["previous"] == 20 and entry["value"] == 8
    assert (await client.get("/api/preferences")).json()["values"]["planner.new_material_min"] == 8
    again = await client.post(f"/api/adaptations/{card.id}/decide", json={"decision": "no"})
    assert again.status_code == 400
    undone = await client.post(f"/api/adaptations/{card.id}/undo")
    assert undone.status_code == 200 and undone.json()["entries"][0]["undone_at"]
    assert (await client.get("/api/preferences")).json()["values"]["planner.new_material_min"] == 20
    assert (await client.post("/api/adaptations/nope/undo")).status_code == 404
    log = (await client.get("/api/adaptations/log")).json()["entries"]
    assert log[0]["decision"] == "try" and not log[0]["in_effect"]


async def test_review_fixes_try_needs_session_expiry_before_plan_and_no_stacking(
    client: AsyncClient, db: AsyncSession
) -> None:
    await load_seed(db, SEED)
    learner_id = (await client.get("/api/learner/me")).json()["id"]
    s1 = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    row = await db.get(models.Session, s1["id"])
    assert row
    card = await adaptation.propose(
        db,
        learner_id,
        what="Shorter",
        why="w",
        pref="planner.new_material_min",
        value=8,
        session=row,
    )
    # 'Try' without a session is refused (it would never expire)
    no_session = await client.post(f"/api/adaptations/{card.id}/decide", json={"decision": "try"})
    assert no_session.status_code == 400
    ok = await client.post(
        f"/api/adaptations/{card.id}/decide", json={"decision": "try", "session_id": s1["id"]}
    )
    assert ok.status_code == 200 and ok.json()["entries"][0]["trial"]
    # an in-effect trial blocks a second card on the same pattern
    again = await adaptation.propose(
        db,
        learner_id,
        what="Shorter",
        why="w",
        pref="planner.new_material_min",
        value=8,
        session=row,
    )
    assert again.id == card.id and (await adaptation.pending(db, learner_id)) == []
    await client.post(f"/api/sessions/{s1['id']}/end", json={"energy_after": 3, "self_report": 3})
    # the next session is planned *after* the trial expired: 20-minute new material, not 8
    s2 = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    new_material = next(b for b in s2["plan"] if b["type"] == "new_material")
    assert new_material["planned_min"] == 20 and new_material["base_min"] == 20
    assert (await client.get("/api/preferences")).json()["values"]["planner.new_material_min"] == 20
    # a plan card cannot be made "the default"
    r = await client.post(
        "/api/plan/replan", json={"session_id": s2["id"], "energy": 1, "from_index": 1}
    )
    bad = await client.post(
        f"/api/adaptations/{r.json()['proposal_id']}/decide", json={"decision": "default"}
    )
    assert bad.status_code == 400
