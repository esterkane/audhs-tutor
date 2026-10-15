"""Block APIs must neither disclose nor mutate another learner's session."""

import pytest

from app.db.models import LearnerProfile, Session
from app.kernel import blocks
from tests._rows import dump_tables


@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("GET", "/api/plan/blocks/state", {}),
        ("POST", "/api/plan/blocks/start", {"index": 0}),
        ("POST", "/api/plan/blocks/end", {"index": 0}),
        ("POST", "/api/plan/blocks/next", {"from_index": 0}),
        ("POST", "/api/plan/blocks/extend", {"index": 0, "minutes": 5}),
        ("POST", "/api/plan/replan", {"energy": 1, "from_index": 0}),
    ],
)
async def test_foreign_session_matches_missing_and_never_writes(
    client, db, db_path, method, path, payload
):
    own_id = (await client.post("/api/sessions", json={})).json()["id"]
    own = await db.get(Session, own_id)
    foreign_owner = LearnerProfile(display_name="Other learner")
    db.add(foreign_owner)
    await db.flush()
    foreign = Session(
        learner_id=foreign_owner.id,
        mode="steady",
        energy=3,
        planned_blocks_json=own.planned_blocks_json,
    )
    db.add(foreign)
    await db.commit()
    await blocks.start(db, foreign, 0)
    before = dump_tables(f"sqlite:///{db_path}")

    async def request(sid):
        if method == "GET":
            return await client.get(path, params={"session_id": sid})
        return await client.post(path, json={**payload, "session_id": sid})

    response = await request(foreign.id)
    missing = await request("missing-session")
    assert response.status_code == missing.status_code == 404
    assert response.json() == missing.json()
    assert dump_tables(f"sqlite:///{db_path}") == before
