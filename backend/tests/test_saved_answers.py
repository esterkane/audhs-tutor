"""Durable answer snapshots, independent of model output quality."""

import asyncio

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.answers import save_completed
from app.db.models import LearnerProfile, Session, TutorAnswer
from app.models_ai.registry import seed_defaults


async def test_turn_dedup_conflict_and_restart(
    db: AsyncSession, learner: LearnerProfile, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    session = Session(learner_id=learner.id, mode="steady", energy=3)
    db.add(session)
    await db.commit()
    args = dict(
        learner_id=learner.id,
        session_id=session.id,
        turn_id="turn-1",
        surface="playground",
        request={"question": "Why?", "code": "x = 1"},
        text="Because x is one.\n",
        metadata={"sources": []},
    )

    async def save() -> str:
        async with session_factory() as connection:
            return (await save_completed(connection, **args)).id

    ids = await asyncio.gather(save(), save())
    assert ids[0] == ids[1]
    async with session_factory() as reopened:
        row = (await reopened.execute(select(TutorAnswer))).scalar_one()
        assert row.text == args["text"] and row.request_json == args["request"]
        with pytest.raises(ValueError, match="different saved answer"):
            await save_completed(reopened, **{**args, "text": "Changed"})
        assert await reopened.scalar(select(func.count()).select_from(TutorAnswer)) == 1
        with pytest.raises(ValueError, match="empty answer"):
            await save_completed(reopened, **{**args, "turn_id": "empty", "text": " "})
        other = LearnerProfile(display_name="Other")
        reopened.add(other)
        await reopened.commit()
        with pytest.raises(KeyError, match="session not found"):
            await save_completed(reopened, **{**args, "learner_id": other.id})


async def test_save_failure_keeps_generated_reply(
    client: AsyncClient, db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.orchestrator import playground

    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()

    async def fail(*args: object, **kwargs: object) -> None:
        raise OperationalError("insert", {}, Exception("disk full"))

    monkeypatch.setattr(playground, "save_completed", fail)
    response = await client.post(
        "/api/playground/tutor",
        json={
            "session_id": session["id"],
            "exercise": "Example",
            "code": "x = 1",
        },
    )
    assert response.status_code == 200
    assert response.json()["text"]
    assert response.json()["answer_id"] is None
    assert "could not be saved" in response.json()["save_error"]
    assert await db.scalar(select(func.count()).select_from(TutorAnswer)) == 0


async def test_commit_failure_rolls_back_snapshot(
    db: AsyncSession,
    learner: LearnerProfile,
    monkeypatch: pytest.MonkeyPatch,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    session = Session(learner_id=learner.id, mode="steady", energy=3)
    db.add(session)
    await db.commit()
    sid, lid = session.id, learner.id

    async def fail() -> None:
        raise OperationalError("commit", {}, Exception("disk full"))

    monkeypatch.setattr(db, "commit", fail)
    with pytest.raises(OperationalError):
        await save_completed(
            db,
            learner_id=lid,
            session_id=sid,
            turn_id="failed",
            surface="playground",
            request={},
            text="Delivered",
            metadata={},
        )
    async with session_factory() as reopened:
        assert await reopened.scalar(select(func.count()).select_from(TutorAnswer)) == 0
