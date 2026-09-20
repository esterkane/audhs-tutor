"""domain-blocks slice: vocab decks on FSRS kept out of the AI/ML review, planner domain block,
practice events, review of a vocab card, skipped movement feeding the adaptation rule."""

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.kernel import memory, planner, practice
from app.kernel import session as ksession
from app.kernel.seed import load_seed
from app.schemas.common import Mode
from tests.test_orchestrator import SEED


async def test_vocab_cards_are_language_domain_and_never_mix_into_ai_review(
    db: AsyncSession, learner: models.LearnerProfile
) -> None:
    await load_seed(db, SEED)
    past = datetime.now(UTC) - timedelta(days=2)
    a = await practice.add_vocab(
        db, learner.id, lang="de", word="der Hund", translation="the dog", now=past
    )
    again = await practice.add_vocab(
        db, learner.id, lang="de", word="Der Hund ", translation="the dog", now=past
    )
    assert again.id == a.id  # idempotent by normalised word
    await practice.add_vocab(
        db,
        learner.id,
        lang="de",
        word="die Katze",
        translation="the cat",
        example="Die Katze schläft.",
        now=past,
    )
    node = await practice.vocab_deck(db, "de")
    assert node.domain == "language" and node.title == "German vocabulary"
    assert await practice.language_due(db, learner.id) == 2
    ai_due = await memory.due_items(db, learner.id, cap=50, exclude_domains=("language",))
    for item, _ in ai_due:
        node_of_item = await db.get(models.SkillNode, item.skill_id)
        assert node_of_item and node_of_item.domain != "language"
    decks = await practice.decks(db, learner.id)
    assert decks == [
        {"lang": "de", "title": "German vocabulary", "node_id": node.id, "cards": 2, "due": 2}
    ]


def test_planner_picks_language_then_guitar() -> None:
    base = dict(mode="steady", energy=3, due_reviews=2, next_skill_id="k", review_node_ids=["a"])
    lang = planner.plan_session(planner.PlanInput(**base, language_due=5, guitar=True))  # type: ignore[arg-type]
    block = next(b for b in lang.blocks if b.type == "domain_switch")
    assert block.domain == "language" and "5 vocabulary cards" in block.reason and block.optional
    guitar = planner.plan_session(planner.PlanInput(**base, language_due=0, guitar=True))  # type: ignore[arg-type]
    assert next(b for b in guitar.blocks if b.type == "domain_switch").domain == "guitar"
    none = planner.plan_session(planner.PlanInput(**base))  # type: ignore[arg-type]
    assert "domain_switch" not in none.types()
    low = planner.plan_session(planner.PlanInput(**{**base, "energy": 2}, language_due=5))  # type: ignore[arg-type]
    assert "domain_switch" not in low.types()  # boundaries only at energy ≥ 3
    movement = next(b for b in lang.blocks if b.type == "movement_primer")
    assert movement.domain == "movement"
    planner.validate_plan(lang)


async def test_practice_event_payload_and_validation(
    db: AsyncSession, learner: models.LearnerProfile
) -> None:
    s = await ksession.start(db, learner.id, mode=Mode.STEADY, energy=3)
    out = await practice.log_practice(
        db,
        learner.id,
        domain="guitar",
        activity="chord changes",
        duration_min=12.5,
        self_rating=4,
        notes="C-G",
        session=s,
    )
    ev = await db.get(models.LearningEvent, out["event_id"])
    assert (
        ev
        and ev.verb == "practiced"
        and ev.domain == "guitar"
        and ev.activity_type == "domain_switch"
    )
    assert ev.result_json == {"duration_min": 12.5, "self_rating": 4}
    assert ev.context_json == {"domain": "guitar", "activity": "chord changes", "notes": "C-G"}
    move = await practice.log_practice(
        db, learner.id, domain="movement", activity="walk 5 minutes", duration_min=5, self_rating=3
    )
    ev2 = await db.get(models.LearningEvent, move["event_id"])
    assert ev2 and ev2.activity_type == "movement" and ev2.session_id is None
    for bad in (dict(domain="cooking"), dict(self_rating=9), dict(duration_min=-1)):
        try:
            await practice.log_practice(
                db,
                learner.id,
                **{"domain": "guitar", "activity": "x", "duration_min": 1, "self_rating": 3, **bad},
            )  # type: ignore[arg-type]
            raise AssertionError(bad)
        except ValueError:
            pass


async def test_routes_vocab_review_practice_and_skipped_movement(
    client: AsyncClient, db: AsyncSession
) -> None:
    await load_seed(db, SEED)
    added = await client.post(
        "/api/vocab",
        json={
            "lang": "de",
            "word": "der Hund",
            "translation": "the dog",
            "example": "Der Hund bellt.",
        },
    )
    assert added.status_code == 201 and added.json()["word"] == "der Hund"
    decks = (await client.get("/api/vocab")).json()
    assert decks["due_total"] == 1 and decks["decks"][0]["lang"] == "de"
    await client.put("/api/preferences", json={"key": "planner.language", "value": True})
    s = (await client.post("/api/sessions", json={"mode": "steady", "energy": 4})).json()
    types = [b["type"] for b in s["plan"]]
    assert (
        "domain_switch" in types
        and next(b for b in s["plan"] if b["type"] == "domain_switch")["domain"] == "language"
    )
    assert s["due_reviews"] == 0  # the vocab card is not an AI/ML review
    ai = (await client.get("/api/review/due", params={"session_id": s["id"]})).json()
    assert all(i["item_type"] != "vocab" for i in ai["items"])
    lang = (
        await client.get("/api/review/due", params={"session_id": s["id"], "domain": "language"})
    ).json()
    assert len(lang["items"]) == 1 and lang["items"][0]["question"] == "der Hund"
    assert (
        lang["items"][0]["reveal"] == "the dog — e.g. Der Hund bellt."
        and lang["items"][0]["skill_title"] == "German vocabulary"
    )
    rated = await client.post(
        f"/api/review/{lang['items'][0]['item_id']}",
        json={"session_id": s["id"], "rating": 3, "confidence_pre": 3},
    )
    assert rated.status_code == 200
    assert (await client.get("/api/vocab")).json()["due_total"] == 0
    acts = (await client.get("/api/practice/activities")).json()["activities"]
    assert acts["movement"][0] == "walk 5 minutes"
    logged = await client.post(
        "/api/practice",
        json={
            "session_id": s["id"],
            "domain": "movement",
            "activity": "stretch",
            "duration_min": 4,
            "self_rating": 4,
        },
    )
    assert logged.status_code == 200 and logged.json()["domain"] == "movement"
    # skipping the movement primer is an early switch with reason "skipped" (feeds movement_skipped)
    idx = types.index("movement_primer") if "movement_primer" in types else None
    if idx is not None:
        await client.post(
            "/api/plan/blocks/start",
            json={"session_id": s["id"], "index": idx, "switched_early": False},
        )
        ended = await client.post(
            "/api/plan/blocks/end",
            json={"session_id": s["id"], "index": idx, "switched_early": True, "reason": "skipped"},
        )
        assert ended.status_code == 200 and ended.json()["allowed"]
        events = (await db.execute(select(models.LearningEvent))).scalars().all()
        assert any(
            e.verb == "block_ended" and (e.result_json or {}).get("reason") == "skipped"
            for e in events
        )
    assert (
        await client.post(
            "/api/practice",
            json={"domain": "cooking", "activity": "x", "duration_min": 1, "self_rating": 3},
        )
    ).status_code == 400
