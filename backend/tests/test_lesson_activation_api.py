import pytest
from sqlalchemy import func, select, update

from app.api.deps import get_learner
from app.db.models import (
    AssessmentAttempt,
    AssessmentTaskReview,
    CurriculumDraft,
    LearnerProfile,
    LessonActivation,
    MemoryState,
    ModelCall,
    TutorAnswer,
)
from tests.test_lesson_activation_commands import prepared


async def post(client, value, key="key"):
    return await client.post(
        "/api/lesson-activations/commands", json=value, headers={"Idempotency-Key": key}
    )


async def test_preview_activation_and_recovery(client, db, learner, session_factory):
    promotion, command = await prepared(db, learner, session_factory)
    path = f"/api/lesson-activations/drafts/{promotion.draft_id}/preview"
    response = await client.get(path)
    assert response.status_code == 200, response.text
    preview = response.json()
    assert preview["command"] == command
    assert preview["skills"] == preview["learning_objects"] == preview["assessments"] == 1
    assert preview["grounding"] == "ungrounded"
    assert any("does not verify" in text for text in preview["warnings"])
    assert "Explanation of root" not in response.text and "snapshot" not in response.text
    assert await db.scalar(select(func.count()).select_from(LessonActivation)) == 0
    await db.commit()
    activated = await post(client, preview["command"])
    assert activated.status_code == 200, activated.text
    receipt = activated.json()
    assert (await post(client, preview["command"])).json() == receipt
    assert (await post(client, preview["command"], "different-key")).status_code == 409
    assert (
        await client.get(f"/api/lesson-activations/{receipt['activation_id']}")
    ).json() == receipt
    recovery = (await client.get(path)).json()
    assert recovery["command"] is None and recovery["receipt"] == receipt
    assert recovery["status"] == "published"
    for model in (AssessmentAttempt, AssessmentTaskReview, MemoryState, ModelCall):
        assert await db.scalar(select(func.count()).select_from(model)) == 0


async def test_preview_disabled_after_source_or_draft_change(client, db, learner, session_factory):
    promotion, command = await prepared(db, learner, session_factory)
    await db.execute(update(TutorAnswer).values(text="Private changed answer"))
    await db.commit()
    response = await client.get(f"/api/lesson-activations/drafts/{promotion.draft_id}/preview")
    assert response.status_code == 200
    assert response.json()["command"] is None
    assert response.json()["issues"]
    assert "Private changed answer" not in response.text
    assert (await post(client, command)).status_code == 409
    assert await db.scalar(select(func.count()).select_from(LessonActivation)) == 0


async def test_foreign_missing_equivalence(client, db, learner, session_factory):
    promotion, command = await prepared(db, learner, session_factory)
    activated = (await post(client, command)).json()
    other = LearnerProfile(display_name="Other")
    db.add(other)
    await db.commit()
    app = client._transport.app

    async def other_learner():
        return other

    app.dependency_overrides[get_learner] = other_learner
    try:
        base = "/api/lesson-activations"
        pairs = [
            (f"{base}/drafts/{promotion.draft_id}/preview", f"{base}/drafts/missing/preview"),
            (f"{base}/{activated['activation_id']}", f"{base}/missing"),
        ]
        for foreign_path, missing_path in pairs:
            foreign, missing = await client.get(foreign_path), await client.get(missing_path)
            assert foreign.status_code == missing.status_code == 404
            assert foreign.json() == missing.json()
        assert (await post(client, command)).status_code == 404
    finally:
        del app.dependency_overrides[get_learner]


@pytest.mark.parametrize("content", [b'{"private":"do not echo"}', b"{broken"])
async def test_invalid_input_not_echoed(client, content):
    response = await client.post(
        "/api/lesson-activations/commands", content=content, headers={"Idempotency-Key": "key"}
    )
    assert response.status_code == 422
    assert "do not echo" not in response.text and "broken" not in response.text


async def test_stream_limit_key_and_extra_owner(client):
    async def chunks():
        yield b" " * 3000
        yield b" " * 2000

    response = await client.post(
        "/api/lesson-activations/commands",
        content=chunks(),
        headers={"Idempotency-Key": "key", "Content-Length": "1"},
    )
    assert response.status_code == 413
    assert (await client.post("/api/lesson-activations/commands", json={})).status_code == 422
    assert (await post(client, {}, " ")).status_code == 422


async def test_invalid_draft_preview_is_not_actionable(client, db, learner, session_factory):
    promotion, _ = await prepared(db, learner, session_factory)
    await db.execute(
        update(CurriculumDraft)
        .where(CurriculumDraft.id == promotion.draft_id)
        .values(payload_json={"skills": []})
    )
    await db.commit()
    response = await client.get(f"/api/lesson-activations/drafts/{promotion.draft_id}/preview")
    assert response.status_code == 200
    assert response.json()["command"] is None and response.json()["issues"]
