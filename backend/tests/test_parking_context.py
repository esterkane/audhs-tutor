import hashlib
import json

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ParkingLotItem


async def test_context_preserved_by_replay_and_promotion(client: AsyncClient):
    context = {
        "version": 1,
        "kind": "project",
        "label": "Example step",
        "course_id": "c",
        "section_id": "s",
        "view": "notebook",
    }
    body = {"request_key": "context-one", "text": "Remember", "original_context": context}
    item = (await client.post("/api/parking", json=body)).json()
    assert item["original_context"] == context
    await client.post(f"/api/parking/{item['id']}/promote", json={})
    replay = (await client.post("/api/parking", json=body)).json()
    assert replay["original_context"] == context and replay["status"] == "promoted"
    assert (
        await client.post(
            "/api/parking", json={**body, "original_context": {**context, "section_id": "other"}}
        )
    ).status_code == 409
    assert (
        await client.post(
            "/api/parking",
            json={"text": "Invalid", "original_context": {**context, "url": "https://example.com"}},
        )
    ).status_code == 422


async def test_pre_context_key_still_replays(client: AsyncClient, db: AsyncSession):
    owner = (await client.get("/api/learner/me")).json()["id"]
    payload = {"session_id": None, "node_id": None, "text": "Before context"}
    row = ParkingLotItem(
        learner_id=owner,
        text=payload["text"],
        request_key="old-key",
        request_fingerprint=hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest(),
    )
    db.add(row)
    await db.commit()
    response = await client.post("/api/parking", json={**payload, "request_key": "old-key"})
    assert response.status_code == 201 and response.json()["id"] == row.id
    assert response.json()["original_context"] is None
