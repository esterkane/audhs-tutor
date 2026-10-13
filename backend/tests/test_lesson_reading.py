from sqlalchemy import func, select, update

from app.api.deps import get_learner
from app.db.models import AssessmentAttempt, LearnerProfile, LearningObject, ModelCall, SkillNode
from tests.test_lesson_activation_api import post
from tests.test_lesson_activation_commands import prepared


async def test_saved_reading_identity_sources_and_no_generation(
    client, db, learner, session_factory
):
    _, command = await prepared(db, learner, session_factory)
    receipt = (await post(client, command)).json()
    path = f"/api/objects/{receipt['skill_ids'][0]}/reading"
    response = await client.get(path)
    assert response.status_code == 200, response.text
    reading = response.json()
    assert reading["passages"] == [
        "Fit a mean on training data, then apply the saved mean.",
        "Training values 2 and 4 have mean 3.",
    ]
    assert reading["object_id"] == receipt["object_ids"][0]
    assert reading["source_ids"] == [] and reading["answer_id"] == "root"
    assert reading["draft_id"] == receipt["draft_id"]
    assert (await client.get(path)).json() == reading
    await db.execute(
        update(LearningObject)
        .where(LearningObject.id == reading["object_id"])
        .values(examples_json=["Edited explanation", "Edited example"])
    )
    await db.commit()
    changed = (await client.get(path)).json()
    assert changed["content_sha256"] != reading["content_sha256"]
    assert changed["passages"][0] == "Edited explanation"
    for model in (AssessmentAttempt, ModelCall):
        assert await db.scalar(select(func.count()).select_from(model)) == 0
    # Newer unlinked content must never silently show an older activation's reading.
    db.add(LearningObject(skill_id=receipt["skill_ids"][0], version=2, concept="New", goal="New"))
    await db.commit()
    assert (await client.get(path)).json() is None


async def test_reading_owner_scope_and_shared_fallback(client, db, learner, session_factory):
    _, command = await prepared(db, learner, session_factory)
    receipt = (await post(client, command)).json()
    other = LearnerProfile(display_name="Other")
    db.add(other)
    db.add(SkillNode(id="shared", slug="shared", domain="ai_ml", title="Shared"))
    await db.commit()
    assert (await client.get("/api/objects/shared/reading")).json() is None
    app = client._transport.app
    app.dependency_overrides[get_learner] = lambda: other
    try:
        foreign = await client.get(f"/api/objects/{receipt['skill_ids'][0]}/reading")
        missing = await client.get("/api/objects/missing/reading")
        assert foreign.status_code == missing.status_code == 404
        assert foreign.json() == missing.json()
    finally:
        del app.dependency_overrides[get_learner]
