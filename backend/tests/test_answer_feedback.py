from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LearnerProfile, LearningEvent, ModelCall, TutorAnswer, TutorAnswerFeedback


async def test_feedback_retries_conflicts_scope_and_suggestion_exclusion(
    client: AsyncClient, db: AsyncSession
) -> None:
    owner = (await client.get("/api/learner/me")).json()["id"]
    other = LearnerProfile(display_name="Other")
    db.add(other)
    await db.commit()
    for id_, learner in [("own", owner), ("foreign", other.id)]:
        db.add(
            TutorAnswer(
                id=id_,
                learner_id=learner,
                turn_id=id_,
                surface="tutor",
                request_json={},
                text="Immutable answer",
                metadata_json={},
                fingerprint=id_,
            )
        )
    await db.commit()
    original = (await client.get("/api/answers/own")).json()
    url = "/api/answers/own/feedback"
    assert (await client.get(url)).json()["revision"] == 0
    state = {
        "verdict": "incorrect",
        "note": "The example has wrong totals",
        "hidden": False,
        "revision": 0,
    }
    first = await client.put(url, json=state)
    assert first.status_code == 200, first.text
    assert first.json()["revision"] == 1
    assert (await client.put(url, json=state)).json() == first.json()
    assert (await client.put(url, json={**state, "verdict": "helpful"})).status_code == 409
    assert (await client.get("/api/answers", params={"suggestions": True})).json()["items"] == []
    assert len((await client.get("/api/answers")).json()["items"]) == 1
    clear = await client.put(
        url, json={"verdict": None, "note": "", "hidden": False, "revision": 1}
    )
    assert clear.json()["revision"] == 2
    assert (
        len((await client.get("/api/answers", params={"suggestions": True})).json()["items"]) == 1
    )
    for identifier in ("foreign", "missing"):
        for method in ("get", "put"):
            response = await client.request(
                method,
                f"/api/answers/{identifier}/feedback",
                **({"json": state} if method == "put" else {}),
            )
            assert response.status_code == 404
    assert (await client.get("/api/answers/own")).json() == original
    assert await db.scalar(select(func.count()).select_from(TutorAnswerFeedback)) == 1
    for model in (ModelCall, LearningEvent):
        assert await db.scalar(select(func.count()).select_from(model)) == 0


async def test_concurrent_feedback_writes_do_not_overwrite(
    db: AsyncSession, client: AsyncClient, session_factory
) -> None:  # type: ignore[no-untyped-def]
    import asyncio

    from app.core.errors import AppError
    from app.db.answer_feedback import save
    from app.schemas.answers import AnswerFeedbackState

    owner = (await client.get("/api/learner/me")).json()["id"]
    db.add(
        TutorAnswer(
            id="race",
            learner_id=owner,
            turn_id="race",
            surface="tutor",
            request_json={},
            text="Original",
            metadata_json={},
            fingerprint="race",
        )
    )
    await db.commit()

    async def write(note: str):  # type: ignore[no-untyped-def]
        async with session_factory() as session:
            try:
                return await save(
                    session, owner, "race", AnswerFeedbackState(verdict="confusing", note=note)
                )
            except AppError as exc:
                return exc.http_status

    results = await asyncio.gather(write("first"), write("second"))
    assert sum(isinstance(result, AnswerFeedbackState) for result in results) == 1
    assert 409 in results
    assert await db.scalar(select(func.count()).select_from(TutorAnswerFeedback)) == 1
