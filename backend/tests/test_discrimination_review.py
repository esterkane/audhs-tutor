from uuid import uuid4

from sqlalchemy import select

from app.db.models import LearnerProfile, MemoryState, ReviewItem, Session, SkillNode
from app.kernel import memory
from app.kernel import session as sessions
from app.kernel.discrimination_review import sync_pair
from tests.test_knowledge_authoring import complete

PAIR = {
    "case_a": "A role can SELECT but sees zero rows.",
    "case_b": "The role lacks SELECT.",
    "failing_case": "b",
    "rationale": "The table grant is required.",
    "schedule_pair": True,
}


async def test_activation_scopes_orders_and_preserves_independent_due_cards(client, db):
    async def publish(pair):
        r = await client.post(
            "/api/knowledge-material/drafts",
            headers={"Idempotency-Key": str(uuid4())},
            json=complete(case_comparison=pair),
        )
        assert r.is_success, r.text
        d = r.json()
        r = await client.post(
            f"/api/curriculum/drafts/{d['id']}/publish", json={"expected_version": d["version"]}
        )
        assert r.is_success, r.text

    await publish({**PAIR, "schedule_pair": False})
    assert not list(await db.scalars(select(ReviewItem)))
    await publish(PAIR)
    a, b = list(await db.scalars(select(ReviewItem).order_by(ReviewItem.created_at)))
    other = await db.scalar(select(SkillNode).where(SkillNode.id != a.skill_id))
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    s = await db.get(Session, session["id"])
    ordinary, _ = await memory.ensure_item(
        db, s.learner_id, other.id, "mcq", {"q": "Unrelated question", "ref": "unrelated"}
    )
    # A separate learner can author the identical pair on the same shared skill.
    foreign = LearnerProfile(display_name="Other")
    db.add(foreign)
    await db.flush()
    await sync_pair(db, foreign.id, a.skill_id, PAIR)
    states = {m.review_item_id: m for m in await db.scalars(select(MemoryState))}
    for index, card in enumerate((a, ordinary, b)):
        states[card.id].due = f"2020-01-0{index + 1}T00:00:00.000+00:00"
    await db.commit()
    original = [
        (i, states[i].due, states[i].fsrs_card_json.copy()) for i in (a.id, b.id, ordinary.id)
    ]

    async def checkpoint(kind, scope=None):
        await sessions.save_checkpoint(
            db, s, {"block_type": kind, "block_status": "running", "scope_skill_ids": scope}
        )

    async def due(domain=None):
        params = {"session_id": s.id, "as_of": "2030-01-01T00:00:00+00:00"}
        if domain:
            params["domain"] = domain
        r = await client.get("/api/review/due", params=params)
        assert r.is_success, r.text
        return [(c["item_id"], c.get("paired_next_id")) for c in r.json()["items"]]

    await checkpoint("retrieval")
    assert await due() == [(a.id, None), (ordinary.id, None), (b.id, None)]
    await checkpoint("interleaved_review")
    assert await due() == [(a.id, b.id), (b.id, None), (ordinary.id, None)]
    assert await due("language") == []
    await checkpoint("interleaved_review", [other.id])
    assert await due() == [(ordinary.id, None)]
    await checkpoint("interleaved_review")
    assert all(
        states[i].due == due_at and states[i].fsrs_card_json == fsrs for i, due_at, fsrs in original
    )
    # The oldest-five cap takes precedence over encouraging a comparison.
    s.mode = "low_capacity"
    extras = []
    for number in range(4):
        extra, state = await memory.ensure_item(
            db, s.learner_id, other.id, "cloze", {"ref": f"older-{number}", "q": "Generic recall."}
        )
        state.due = f"2020-01-02T00:00:0{number + 1}.000+00:00"
        extras.append(extra)
    await db.commit()
    assert await due() == [(i.id, None) for i in [a, ordinary, *extras[:3]]]
    for extra in extras:
        extra.active = False
    s.mode = "steady"
    await db.commit()
    states[b.id].due = "2031-01-01T00:00:00.000+00:00"
    await db.commit()
    assert await due() == [(a.id, None), (ordinary.id, None)]
    states[b.id].due = original[1][1]
    b.active = False
    await db.commit()
    assert await due() == [(a.id, None), (ordinary.id, None)]
    await sync_pair(db, s.learner_id, a.skill_id, PAIR)
    await db.commit()
    assert await due() == [(a.id, b.id), (b.id, None), (ordinary.id, None)]
    await sync_pair(db, s.learner_id, a.skill_id, {**PAIR, "schedule_pair": False})
    await db.commit()
    assert await due() == [(ordinary.id, None)]
    assert all(
        states[i].due == due_at and states[i].fsrs_card_json == fsrs for i, due_at, fsrs in original
    )
