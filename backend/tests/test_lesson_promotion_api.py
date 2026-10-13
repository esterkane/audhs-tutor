import pytest
from sqlalchemy import func, select, update

from app.api.deps import get_learner
from app.db.models import CurriculumDraft, LearnerProfile, LessonPromotion, ModelCall, TutorAnswer
from tests.test_lesson_promotion_commands import body


async def post(client, value, key="key"):
    return await client.post(
        "/api/lesson-promotions/drafts", json=value, headers={"Idempotency-Key": key}
    )


async def test_preview_create_replay_conflict_and_readback(client, db, learner):
    command = await body(db, learner)
    response = await client.get("/api/lesson-promotions/answers/root/preview")
    assert response.status_code == 200, response.text
    preview = response.json()
    assert preview["binding"] == command["binding"]
    assert preview["publication_available"] is False
    assert "snapshot" not in response.text and "Explanation of root" not in response.text
    assert await db.scalar(select(func.count()).select_from(CurriculumDraft)) == 0
    await db.commit()
    first = await post(client, command)
    assert first.status_code == 200, first.text
    assert (await post(client, command)).json() == first.json()
    assert (await post(client, {**command, "title": "Different"})).status_code == 409
    draft_id = first.json()["draft_id"]
    draft = (await client.get(f"/api/curriculum/drafts/{draft_id}")).json()
    assert draft["status"] == "draft" and draft["payload"]["assessments"][0]["kind"] == "transfer"
    assert (
        await client.post(
            f"/api/curriculum/drafts/{draft_id}/publish", json={"expected_version": 1}
        )
    ).status_code == 409
    assert await db.scalar(select(func.count()).select_from(ModelCall)) == 0


async def test_missing_foreign_and_stale_targets(client, db, learner):
    command = await body(db, learner)
    other = LearnerProfile(display_name="Other")
    db.add(other)
    await db.commit()
    app = client._transport.app

    async def other_owner():
        return other

    app.dependency_overrides[get_learner] = other_owner
    try:
        foreign = await client.get("/api/lesson-promotions/answers/root/preview")
        missing = await client.get("/api/lesson-promotions/answers/missing/preview")
        assert foreign.status_code == missing.status_code == 404
        assert foreign.json() == missing.json()
        assert (await post(client, command)).status_code == 404
    finally:
        del app.dependency_overrides[get_learner]
    await db.execute(update(TutorAnswer).where(TutorAnswer.id == "root").values(text="Changed"))
    await db.commit()
    assert (await post(client, command)).status_code == 409
    assert await db.scalar(select(func.count()).select_from(LessonPromotion)) == 0


@pytest.mark.parametrize("raw", [b'{"private":"do not echo"}', b"{broken"])
async def test_invalid_body_does_not_echo_content(client, raw):
    response = await client.post(
        "/api/lesson-promotions/drafts", content=raw, headers={"Idempotency-Key": "bad"}
    )
    assert response.status_code == 422
    assert "do not echo" not in response.text and "broken" not in response.text


async def test_streamed_body_limit_and_required_request_key(client):
    async def chunks():
        yield b" " * 40000
        yield b" " * 30000

    response = await client.post(
        "/api/lesson-promotions/drafts",
        content=chunks(),
        headers={"Idempotency-Key": "large", "Content-Length": "1"},
    )
    assert response.status_code == 413
    assert (await client.post("/api/lesson-promotions/drafts", json={})).status_code == 422
