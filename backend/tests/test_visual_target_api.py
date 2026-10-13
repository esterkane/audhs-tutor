from sqlalchemy import func, select

from app.api.deps import get_learner
from app.db.models import LearnerProfile, LearningEvent, ModelCall, TutorAnswer
from tests.test_authored_visual_commands import ask_spec


async def test_exact_target_without_generation_or_raw_snapshot(client, db, learner):
    spec = await ask_spec(db, learner, sourced=True)
    response = await client.get("/api/authored-visuals/answer-target/root")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["binding"] == spec["binding"]
    assert data["grounding"] == "sources_recorded"
    assert data["source_chunk_ids"] == ["chunk"]
    assert data["sources_omitted"] == 0
    assert data["meaning"] == "target_snapshot_not_approval"
    assert "snapshot_json" not in data and "text" not in data
    assert await db.scalar(select(func.count()).select_from(ModelCall)) == 0
    assert await db.scalar(select(func.count()).select_from(LearningEvent)) == 0
    original = data["binding"]["answer_sha256"]
    (await db.get(TutorAnswer, "root")).text = "A revised answer"
    await db.commit()
    assert (await client.get("/api/authored-visuals/answer-target/root")).json()["binding"][
        "answer_sha256"
    ] != original


async def test_legacy_and_foreign_target_fail_closed(client, db, learner):
    await ask_spec(db, learner)
    assert (await client.get("/api/authored-visuals/answer-target/root")).json()[
        "grounding"
    ] == "ungrounded"
    (await db.get(TutorAnswer, "root")).metadata_json = {}
    await db.commit()
    legacy = (await client.get("/api/authored-visuals/answer-target/root")).json()
    assert legacy["grounding"] == "unknown"
    assert legacy["issues"]
    other = LearnerProfile(display_name="Other")
    db.add(other)
    await db.commit()

    async def other_owner():
        return other

    app = client._transport.app
    app.dependency_overrides[get_learner] = other_owner
    try:
        foreign = await client.get("/api/authored-visuals/answer-target/root")
        missing = await client.get("/api/authored-visuals/answer-target/missing")
        assert foreign.status_code == missing.status_code == 404
        assert foreign.json() == missing.json()
    finally:
        del app.dependency_overrides[get_learner]
