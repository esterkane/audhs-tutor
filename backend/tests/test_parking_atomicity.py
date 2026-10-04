"""A rejected audit write must not leave a saved or promoted thought behind."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.events import EventWriter
from app.db.models import LearningEvent, ParkingLotItem


@pytest.mark.parametrize("with_session", [False, True])
async def test_failed_park_event_rolls_back_thought(
    client: AsyncClient, db: AsyncSession, monkeypatch: pytest.MonkeyPatch, with_session: bool
) -> None:
    body: dict[str, str] = {"text": "Keep this idea for later"}
    if with_session:
        response = await client.post("/api/sessions", json={"mode": "steady", "energy": 3})
        assert response.status_code == 201
        body["session_id"] = response.json()["id"]
    original = EventWriter.emit

    async def fail(*args: object, **kwargs: object) -> None:
        raise RuntimeError("injected audit failure")

    monkeypatch.setattr(EventWriter, "emit", fail)
    with pytest.raises(RuntimeError, match="injected audit failure"):
        await client.post("/api/parking", json=body)
    assert list((await db.scalars(select(ParkingLotItem))).all()) == []
    monkeypatch.setattr(EventWriter, "emit", original)
    saved = await client.post("/api/parking", json=body)
    assert saved.status_code == 201
    item_id = saved.json()["id"]
    assert await db.get(ParkingLotItem, item_id) is not None
    events = (
        await db.scalars(select(LearningEvent).where(LearningEvent.object_id == item_id))
    ).all()
    assert len(events) == 1 and events[0].verb == "parked"


async def test_failed_promotion_event_preserves_parked_status(
    client: AsyncClient, db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved = await client.post("/api/parking", json={"text": "An optional reminder"})
    assert saved.status_code == 201
    item_id = saved.json()["id"]

    async def fail(*args: object, **kwargs: object) -> None:
        raise RuntimeError("injected audit failure")

    monkeypatch.setattr(EventWriter, "emit", fail)
    with pytest.raises(RuntimeError, match="injected audit failure"):
        await client.post(f"/api/parking/{item_id}/promote", json={})
    item = await db.get(ParkingLotItem, item_id)
    assert item is not None and item.status == "parked" and item.promoted_to is None
