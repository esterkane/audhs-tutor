from sqlalchemy import func, select

from app.db.models import LearnerProfile, LearningEvent, ModelCall, TutorAnswer


async def seed(client, db):
    owner = (await client.get("/api/learner/me")).json()["id"]
    other = LearnerProfile(display_name="Other")
    db.add(other)
    await db.commit()
    for identity, learner, parent, purpose in [
        ("original", owner, None, None),
        ("correction", owner, "original", "correction"),
        ("another", owner, "original", "correction"),
        ("followup", owner, "original", "followup"),
        ("unrelated", owner, None, "correction"),
        ("foreign", other.id, "original", "correction"),
    ]:
        db.add(
            TutorAnswer(
                id=identity,
                learner_id=learner,
                turn_id=identity,
                surface="playground",
                request_json={"question": identity},
                text=f"Immutable {identity}",
                fingerprint=identity,
                metadata_json={"parent_answer_id": parent, "followup_purpose": purpose},
            )
        )
    await db.commit()


async def test_reviewed_choice_retry_conflict_undo_and_history(client, db, fake_local):
    await seed(client, db)
    url = "/api/answers/original/replacement"
    assert (await client.get(url)).json() == {"replacement_id": None, "revision": 0}
    choice = {"replacement_id": "correction", "revision": 0}
    result = await client.put(url, json=choice)
    assert result.status_code == 200
    assert result.json() == {"replacement_id": "correction", "revision": 1}
    assert (await client.put(url, json=choice)).json() == result.json()
    assert (
        await client.put(url, json={"replacement_id": "another", "revision": 0})
    ).status_code == 409
    suggestions = (await client.get("/api/answers", params={"suggestions": True})).json()
    assert "original" not in [row["id"] for row in suggestions["items"]]
    assert (await client.get("/api/answers/original")).json()["text"] == "Immutable original"
    assert "original" in [row["id"] for row in (await client.get("/api/answers")).json()["items"]]
    undone = await client.put(url, json={"replacement_id": None, "revision": 1})
    assert undone.json() == {"replacement_id": None, "revision": 2}
    assert "original" in [
        row["id"]
        for row in (await client.get("/api/answers", params={"suggestions": True})).json()["items"]
    ]
    assert fake_local.calls == []
    for table in (ModelCall, LearningEvent):
        assert await db.scalar(select(func.count()).select_from(table)) == 0


async def test_replacement_rejects_self_foreign_unrelated_unreviewable_targets(client, db):
    await seed(client, db)
    url = "/api/answers/original/replacement"
    for target, code in [
        ("original", 422),
        ("followup", 422),
        ("unrelated", 422),
        ("foreign", 404),
        ("missing", 404),
    ]:
        assert (
            await client.put(url, json={"replacement_id": target, "revision": 0})
        ).status_code == code
    await client.put("/api/answers/correction/feedback", json={"verdict": "incorrect"})
    assert (
        await client.put(url, json={"replacement_id": "correction", "revision": 0})
    ).status_code == 409
    assert (await client.get("/api/answers/foreign/replacement")).status_code == 404
    assert (await client.get(url)).json()["revision"] == 0


async def test_concurrent_replacement_choices_keep_one_winner(client, db, session_factory):
    import asyncio

    from app.core.errors import AppError
    from app.db.answer_replacement import save
    from app.schemas.answers import AnswerReplacementState

    await seed(client, db)
    owner = (await client.get("/api/learner/me")).json()["id"]

    async def choose(target):
        async with session_factory() as connection:
            try:
                return await save(
                    connection, owner, "original", AnswerReplacementState(replacement_id=target)
                )
            except AppError as error:
                return error.http_status

    results = await asyncio.gather(choose("correction"), choose("another"))
    assert sum(isinstance(item, AnswerReplacementState) for item in results) == 1
    assert 409 in results
