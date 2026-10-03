"""Review retries must not update FSRS twice or cross learner boundaries."""

from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.db import models
from app.kernel import memory
from app.kernel.seed import load_seed

KEY = "dda91f70-cd1d-44aa-850b-174ea74aa875"
HEADERS = {"Idempotency-Key": KEY}
SEED = Path(__file__).resolve().parents[2] / "seeds" / "attention"


async def prepare(client, db):
    await load_seed(db, SEED)
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    owner = await db.get(models.Session, session["id"])
    node = await db.scalar(select(models.SkillNode))
    item, _ = await memory.ensure_item(db, owner.learner_id, node.id, "mcq", {"ref": "review-test"})
    shown = (
        await client.get(f"/api/review/items/{item.id}", params={"session_id": session["id"]})
    ).json()
    return item.id, {
        "session_id": session["id"],
        "rating": 4,
        "hint_count": 1,
        "content_version": shown["content_version"],
    }


async def test_review_lost_response_replays_one_schedule(client, db):
    item, body = await prepare(client, db)
    first = await client.post(f"/api/review/{item}", json=body, headers=HEADERS)
    assert first.status_code == 200
    second = await client.post(f"/api/review/{item}", json=body, headers=HEADERS)
    assert second.json() == first.json()
    assert await db.scalar(select(func.count()).select_from(models.ReviewLog)) == 1
    assert (
        await db.scalar(
            select(func.count())
            .select_from(models.LearningEvent)
            .where(models.LearningEvent.verb == "reviewed")
        )
        == 1
    )
    log = await db.scalar(select(models.ReviewLog))
    assert log.rating == 2  # assisted recall stays capped at Hard
    conflict = await client.post(f"/api/review/{item}", json={**body, "rating": 3}, headers=HEADERS)
    assert conflict.status_code == 409


@pytest.mark.parametrize("surface", ["due", "rate"])
async def test_review_rejects_foreign_session(client, db, surface):
    item, body = await prepare(client, db)
    other = models.LearnerProfile(display_name="Other")
    db.add(other)
    await db.commit()
    session = models.Session(learner_id=other.id, mode="steady", energy=3)
    db.add(session)
    await db.commit()
    errors = []
    for identity in [session.id, "missing"]:
        response = (
            await client.get("/api/review/due", params={"session_id": identity})
            if surface == "due"
            else await client.post(
                f"/api/review/{item}", json={**body, "session_id": identity}, headers=HEADERS
            )
        )
        assert response.status_code == 404
        errors.append(response.json())
    assert errors[0] == errors[1]
    assert await db.scalar(select(func.count()).select_from(models.ReviewLog)) == 0


async def test_lookup_is_read_only_and_survives_reconnect(client, db, session_factory):
    from app.kernel.review_requests import lookup

    item, body = await prepare(client, db)
    url = f"/api/review/requests/{KEY}"
    assert (await client.get(url, params={"session_id": body["session_id"]})).json()[
        "status"
    ] == "not_found"
    rated = await client.post(f"/api/review/{item}", json=body, headers=HEADERS)
    session = await db.get(models.Session, body["session_id"])
    session.ended_at = "2026-10-03T00:00:00Z"
    await db.commit()
    async with session_factory() as reopened:
        found = await lookup(reopened, session.learner_id, session.id, KEY)
        assert found.result.model_dump() == rated.json()
    assert (
        await client.post(f"/api/review/{item}", json=body, headers=HEADERS)
    ).json() == rated.json()
    assert await db.scalar(select(func.count()).select_from(models.ReviewLog)) == 1
    other = models.Session(learner_id=session.learner_id, mode="steady", energy=3)
    db.add(other)
    await db.commit()
    assert (await client.get(url, params={"session_id": other.id})).json()["status"] == "not_found"


async def test_concurrent_equal_rating_is_not_applied_twice(client, db, monkeypatch):
    import asyncio

    item, body = await prepare(client, db)
    entered, release = asyncio.Event(), asyncio.Event()
    original = memory.review

    async def delayed(*args, **kwargs):
        entered.set()
        await release.wait()
        return await original(*args, **kwargs)

    monkeypatch.setattr(memory, "review", delayed)
    from app.db import workspace_requests

    duplicate_entered = asyncio.Event()
    original_claim = workspace_requests.claim
    claim_calls = 0

    async def observed_claim(*args, **kwargs):
        nonlocal claim_calls
        claim_calls += 1
        if claim_calls == 2:
            duplicate_entered.set()
        return await original_claim(*args, **kwargs)

    monkeypatch.setattr(workspace_requests, "claim", observed_claim)
    first = asyncio.create_task(client.post(f"/api/review/{item}", json=body, headers=HEADERS))
    duplicate = None
    try:
        await asyncio.wait_for(entered.wait(), 5)
        duplicate = asyncio.create_task(
            client.post(f"/api/review/{item}", json=body, headers=HEADERS)
        )
        await asyncio.wait_for(duplicate_entered.wait(), 5)
    finally:
        release.set()
        tasks = [first] if duplicate is None else [first, duplicate]
        responses = await asyncio.gather(*tasks)
    assert duplicate is not None
    first_response, duplicate_response = responses
    assert first_response.status_code == 200
    if duplicate_response.status_code == 200:
        assert duplicate_response.json() == first_response.json()
    else:
        assert duplicate_response.status_code == 409
        assert duplicate_response.json()["error"]["code"] == "request_unresolved"
    assert await db.scalar(select(func.count()).select_from(models.ReviewLog)) == 1
    assert (
        await db.scalar(
            select(func.count())
            .select_from(models.LearningEvent)
            .where(models.LearningEvent.verb == "reviewed")
        )
        == 1
    )


@pytest.mark.parametrize("stage", ["review", "complete"])
async def test_failed_rating_rolls_back_card_log_event_and_outcome(
    client, db, session_factory, monkeypatch, stage
):
    from app.db import workspace_requests

    item, body = await prepare(client, db)
    async with session_factory() as connection:
        before = list((await connection.execute(select(models.MemoryState.__table__))).mappings())
    module, name = (memory, "review") if stage == "review" else (workspace_requests, "complete")
    original = getattr(module, name)

    async def fail(*args, **kwargs):
        await original(*args, **kwargs)
        raise RuntimeError("injected review interruption")

    monkeypatch.setattr(module, name, fail)
    with pytest.raises(RuntimeError, match="injected review interruption"):
        await client.post(f"/api/review/{item}", json=body, headers=HEADERS)
    async with session_factory() as connection:
        assert (
            list((await connection.execute(select(models.MemoryState.__table__))).mappings())
            == before
        )
        assert await connection.scalar(select(func.count()).select_from(models.ReviewLog)) == 0
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(models.LearningEvent)
                .where(models.LearningEvent.verb == "reviewed")
            )
            == 0
        )
    found = await client.get(
        f"/api/review/requests/{KEY}", params={"session_id": body["session_id"]}
    )
    assert found.json() == {"status": "unresolved", "result": None}


async def test_distinct_concurrent_ratings_use_successive_card_states(client, db, monkeypatch):
    import asyncio

    from app.db import workspace_requests

    item, body = await prepare(client, db)
    both_claimed = asyncio.Event()
    claims = 0
    original = workspace_requests.claim

    async def barrier(*args, **kwargs):
        nonlocal claims
        result = await original(*args, **kwargs)
        claims += 1
        if claims == 2:
            both_claimed.set()
        await asyncio.wait_for(both_claimed.wait(), 5)
        return result

    monkeypatch.setattr(workspace_requests, "claim", barrier)
    replies = await asyncio.gather(
        client.post(f"/api/review/{item}", json=body, headers=HEADERS),
        client.post(
            f"/api/review/{item}",
            json=body,
            headers={"Idempotency-Key": "28783373-2e03-482c-a6a0-aac86b87cb24"},
        ),
    )
    assert all(reply.status_code == 200 for reply in replies)
    assert await db.scalar(select(func.count()).select_from(models.ReviewLog)) == 2
    events = list(
        (
            await db.execute(
                select(models.LearningEvent)
                .where(
                    models.LearningEvent.verb == "reviewed",
                )
                .order_by(models.LearningEvent.ts, models.LearningEvent.id)
            )
        ).scalars()
    )
    assert len(events) == 2
    assert events[0].result_json["stability_before"] is None
    assert events[1].result_json["stability_before"] == events[0].result_json["stability_after"]
