"""Save intents survive lost responses without duplicate thoughts or audit events."""

import asyncio

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LearningEvent


@pytest.mark.parametrize("with_session", [False, True])
async def test_save_replay_and_conflict(client: AsyncClient, db: AsyncSession, with_session: bool):
    body = {"text": "Remember the example", "request_key": "intent-one"}
    if with_session:
        session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
        body["session_id"] = session["id"]
    saved = await client.post("/api/parking", json=body)
    assert saved.status_code == 201
    item = saved.json()
    assert (await client.post("/api/parking", json=body)).json() == item
    conflict = await client.post("/api/parking", json={**body, "text": "Changed text"})
    assert conflict.status_code == 409
    await client.post(f"/api/parking/{item['id']}/drop")
    replay = (await client.post("/api/parking", json=body)).json()
    assert replay["id"] == item["id"] and replay["status"] == "dropped"
    events = (
        await db.scalars(select(LearningEvent).where(LearningEvent.object_id == item["id"]))
    ).all()
    assert len(events) == 2
    assert sum(event.verb == "parked" for event in events) == 1


async def test_concurrent_save_replays(client: AsyncClient):
    await client.get("/api/learner/me")
    body = {"text": "One thought", "request_key": "concurrent-intent"}
    responses = await asyncio.gather(*(client.post("/api/parking", json=body) for _ in range(5)))
    assert all(response.status_code == 201 for response in responses)
    assert len({response.json()["id"] for response in responses}) == 1
    assert len((await client.get("/api/parking")).json()["items"]) == 1
