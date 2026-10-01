import pytest
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.answer_vectors import load, put
from app.db.models import TutorAnswer, TutorAnswerFeedback, TutorAnswerVector


async def test_cache_owner_version_feedback_and_deletion(
    client: AsyncClient, db: AsyncSession
) -> None:
    owner = (await client.get("/api/learner/me")).json()["id"]
    answer = TutorAnswer(
        id="cached",
        learner_id=owner,
        turn_id="cached",
        surface="playground",
        request_json={},
        metadata_json={},
        text="Answer",
        fingerprint="v1",
    )
    db.add(answer)
    await db.commit()
    assert not await put(db, "other", "cached", "v1", "model:v1", [1.0, 0.0])
    assert not await put(db, owner, "cached", "old", "model:v1", [1.0, 0.0])
    assert await put(db, owner, "cached", "v1", "model:v1", [1.0, 0.0])
    assert await load(db, owner, ["cached"], "model:v1", 2) == {"cached": [1.0, 0.0]}
    assert await load(db, "other", ["cached"], "model:v1", 2) == {}
    assert await load(db, owner, ["cached"], "model:v2", 2) == {}
    assert await load(db, owner, ["cached"], "model:v1", 3) == {}
    feedback = TutorAnswerFeedback(learner_id=owner, answer_id="cached", hidden=True)
    db.add(feedback)
    await db.commit()
    assert await load(db, owner, ["cached"], "model:v1", 2) == {}
    feedback.hidden = False
    feedback.verdict = "incorrect"
    await db.commit()
    assert await load(db, owner, ["cached"], "model:v1", 2) == {}
    feedback.verdict = None
    await db.commit()
    assert await put(db, owner, "cached", "v1", "model:v2", [0.0, 1.0])
    assert await load(db, owner, ["cached"], "model:v1", 2) == {}
    assert await load(db, owner, ["cached"], "model:v2", 2) == {"cached": [0.0, 1.0]}
    # Defensive against imported/corrupt cache content.
    from sqlalchemy import select

    cached = await db.scalar(select(TutorAnswerVector))
    cached.vector_json = ["invalid", 0]
    await db.commit()
    assert await load(db, owner, ["cached"], "model:v2", 2) == {}
    await db.delete(feedback)
    await db.execute(delete(TutorAnswer).where(TutorAnswer.id == "cached"))
    await db.commit()
    assert await db.scalar(select(TutorAnswerVector)) is None


@pytest.mark.parametrize(
    "vector", [[], [0.0, 0.0], [float("nan")], [float("inf")], [True], [1.0] * 8193]
)
async def test_rejects_invalid_vectors(db: AsyncSession, vector: list[float]) -> None:
    with pytest.raises(ValueError):
        await put(db, "owner", "answer", "fingerprint", "model:v1", vector)
