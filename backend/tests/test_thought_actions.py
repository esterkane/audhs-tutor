import asyncio

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.events import EventWriter
from app.db.models import ParkingLotItem, ThoughtAction


async def saved(client):
    return (
        await client.post(
            "/api/parking",
            json={
                "text": "Remember",
                "original_context": {
                    "version": 1,
                    "kind": "source",
                    "label": "Original",
                    "chunk_id": "one",
                },
            },
        )
    ).json()


async def test_undo_and_replay_preserve_original(client: AsyncClient):
    item = await saved(client)
    url = f"/api/parking/{item['id']}/actions"
    body = {"request_key": "promote", "expected_revision": 0, "action": "promote"}
    action = (await client.post(url, json=body)).json()
    assert action["item"]["status"] == "promoted" and action["can_undo"]
    undo = {
        "request_key": "undo",
        "expected_revision": 1,
        "action": "undo",
        "undo_of": action["action_id"],
    }
    restored = (await client.post(url, json=undo)).json()
    assert restored["item"]["status"] == "parked"
    assert restored["item"]["original_context"] == item["original_context"]
    assert restored["item"]["revision"] == 2 and not restored["can_undo"]
    replay = (await client.post(url, json=body)).json()
    assert replay["action_id"] == action["action_id"] and replay["item"]["revision"] == 2
    assert not replay["can_undo"]
    assert (await client.post(url, json=undo)).json() == restored
    assert (await client.post(url, json={**body, "action": "drop"})).status_code == 409


async def test_drop_undo_and_legacy_change_blocks_stale_undo(client: AsyncClient):
    item = await saved(client)
    url = f"/api/parking/{item['id']}/actions"
    await client.post(f"/api/parking/{item['id']}/promote", json={})
    action = (
        await client.post(
            url, json={"request_key": "drop", "expected_revision": 1, "action": "drop"}
        )
    ).json()
    restored = (
        await client.post(
            url,
            json={
                "request_key": "undo",
                "expected_revision": 2,
                "action": "undo",
                "undo_of": action["action_id"],
            },
        )
    ).json()
    assert (
        restored["item"]["status"] == "promoted"
        and restored["item"]["promoted_to"] == "next_session"
    )
    await client.post(f"/api/parking/{item['id']}/drop")
    assert (
        await client.post(
            url,
            json={
                "request_key": "stale",
                "expected_revision": 4,
                "action": "undo",
                "undo_of": action["action_id"],
            },
        )
    ).status_code == 409


async def test_concurrent_actions_and_atomic_failure(
    client: AsyncClient, db: AsyncSession, monkeypatch
):
    item = await saved(client)
    url = f"/api/parking/{item['id']}/actions"
    body = {"request_key": "parallel", "expected_revision": 0, "action": "drop"}
    responses = await asyncio.gather(*(client.post(url, json=body) for _ in range(4)))
    assert all(r.status_code == 200 for r in responses)
    assert len({r.json()["action_id"] for r in responses}) == 1
    assert await db.scalar(select(func.count()).select_from(ThoughtAction)) == 1
    item2 = await saved(client)
    url2 = f"/api/parking/{item2['id']}/actions"
    responses = await asyncio.gather(
        *(client.post(url2, json={**body, "request_key": f"race-{i}"}) for i in range(2))
    )
    assert sorted(r.status_code for r in responses) == [200, 409]
    item3 = await saved(client)

    async def fail(*args, **kwargs):
        raise RuntimeError("audit failed")

    monkeypatch.setattr(EventWriter, "emit", fail)
    with pytest.raises(RuntimeError):
        await client.post(
            f"/api/parking/{item3['id']}/actions", json={**body, "request_key": "failed"}
        )
    row = await db.get(ParkingLotItem, item3["id"])
    assert row.status == "parked" and row.revision == 0
    assert (
        await db.scalar(select(ThoughtAction).where(ThoughtAction.request_key == "failed")) is None
    )
