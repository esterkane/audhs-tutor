from sqlalchemy import func, select

from app.db.models import LearningEvent, ModelCall, TutorAnswer, TutorAnswerFeedback


def answer(owner, identity, question, **metadata):
    return TutorAnswer(
        learner_id=owner,
        id=identity,
        turn_id=identity,
        surface="ask",
        request_json={"question": question},
        text="A saved explanation.",
        fingerprint=identity,
        metadata_json=metadata,
    )


async def test_suggestions_rank_relevant_feedback_and_keep_exclusions(client, db):
    owner = (await client.get("/api/learner/me")).json()["id"]
    rows = [
        answer(owner, "1-helpful", "Explain Python lists"),
        answer(owner, "2-neutral", "Explain Python lists"),
        answer(owner, "3-confusing", "Explain Python lists"),
        answer(owner, "4-wrong", "Explain Python lists"),
        answer(owner, "5-unrelated", "Explain music chords"),
        answer(owner, "6-stale", "Explain Python lists", sources=[{"chunk_id": "missing"}]),
        answer(owner, "7-context", "Explain Python lists", parent_answer_id="1-helpful"),
    ]
    db.add_all(rows)
    await db.flush()
    for identity, verdict in [
        ("1-helpful", "helpful"),
        ("3-confusing", "confusing"),
        ("4-wrong", "incorrect"),
        ("5-unrelated", "helpful"),
        ("6-stale", "helpful"),
    ]:
        db.add(TutorAnswerFeedback(learner_id=owner, answer_id=identity, verdict=verdict))
    await db.commit()
    response = await client.get("/api/ask/suggestions", params={"q": "Python lis", "limit": 10})
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert [item["id"] for item in items] == [
        "1-helpful",
        "2-neutral",
        "3-confusing",
        "6-stale",
        "7-context",
    ]
    assert "You marked it helpful (not a correctness check)" in items[0]["suggestion_reason"]
    assert items[3]["source_check"]["sources"][0]["status"] == "missing"
    assert items[4]["context_dependent"]
    for model in (ModelCall, LearningEvent):
        assert await db.scalar(select(func.count()).select_from(model)) == 0


async def test_exact_text_survives_candidate_bound_and_area_scope(client, db):
    owner = (await client.get("/api/learner/me")).json()["id"]
    db.add(answer(owner, "000", "What is Python?", area_id="chosen"))
    db.add(answer(owner, "999", "What is Python?", area_id="other"))
    for i in range(110):
        db.add(answer(owner, f"recent-{i:03d}", "What is Python used for?", area_id="chosen"))
    await db.commit()
    response = await client.get(
        "/api/ask/suggestions", params={"q": "What is Python?", "area_id": "chosen"}
    )
    items = response.json()["items"]
    assert len(items) == 5 and items[0]["id"] == "000"
    assert items[0]["suggestion_reason"] == "Same question text"
    assert all(item["area_id"] == "chosen" for item in items)
    assert (
        await client.get("/api/ask/suggestions", params={"q": '" OR NOT', "limit": 11})
    ).status_code == 422


async def test_suggestions_are_owned_and_recheck_feedback_without_cached_ranking(client, db):
    from app.db.answer_suggestions import ranked

    owner = (await client.get("/api/learner/me")).json()["id"]
    db.add(answer(owner, "a", "What is a list?"))
    await db.commit()
    assert not await ranked(db, "another-learner", "list", None, 5)
    assert len((await client.get("/api/ask/suggestions?q=list")).json()["items"]) == 1
    db.add(TutorAnswerFeedback(learner_id=owner, answer_id="a", verdict="outdated"))
    await db.commit()
    assert not (await client.get("/api/ask/suggestions?q=list")).json()["items"]
    assert (await client.get("/api/answers/a")).status_code == 200
