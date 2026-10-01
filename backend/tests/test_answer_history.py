"""History lookup is scoped, bounded and has no generation/progress side effects."""

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LearnerProfile, LearningEvent, ModelCall, TutorAnswer
from app.models_ai.fake import FakeProvider


async def test_history_is_scoped_paginated_and_model_free(
    client: AsyncClient, db: AsyncSession, fake_local: FakeProvider
) -> None:
    owner = (await client.get("/api/learner/me")).json()["id"]
    other = LearnerProfile(display_name="Other")
    db.add(other)
    await db.commit()
    for id_, learner, skill, area, surface in [
        ("01", owner, "skill-a", "area-a", "tutor"),
        ("02", owner, "skill-b", "area-a", "tutor"),
        ("03", owner, None, None, "playground"),
        ("04", other.id, "skill-a", "area-a", "tutor"),
    ]:
        db.add(
            TutorAnswer(
                id=id_,
                learner_id=learner,
                turn_id=id_,
                session_id=None,
                surface=surface,
                request_json={"text": f"Request {id_}"},
                text=f"Exact answer {id_}\n",
                metadata_json={"skill_id": skill, "area_id": area},
                fingerprint=id_,
            )
        )
    await db.commit()
    page = (await client.get("/api/answers", params={"limit": 2})).json()
    assert [x["id"] for x in page["items"]] == ["03", "02"]
    assert "request" not in page["items"][0]  # bounded preview, no full code snapshot in list
    assert page["next_cursor"] == "02"
    next_page = (await client.get("/api/answers", params={"cursor": "02", "limit": 2})).json()
    assert [x["id"] for x in next_page["items"]] == ["01"]
    assert next_page["next_cursor"] is None
    area = (await client.get("/api/answers", params={"area_id": "area-a"})).json()
    assert [x["id"] for x in area["items"]] == ["02", "01"]
    skill = (await client.get("/api/answers", params={"skill_id": "skill-a"})).json()
    assert [x["id"] for x in skill["items"]] == ["01"]
    surface = (await client.get("/api/answers", params={"surface": "playground"})).json()
    assert [x["id"] for x in surface["items"]] == ["03"]
    assert (await client.get("/api/answers", params={"skill_id": "absent"})).json()["items"] == []
    detail = (await client.get("/api/answers/01")).json()
    assert detail["text"] == "Exact answer 01\n" and detail["request"]["text"] == "Request 01"
    for prefix in ("/api/answers/", "/api/answers?cursor="):
        foreign = await client.get(prefix + "04")
        missing = await client.get(prefix + "missing")
        assert foreign.status_code == missing.status_code == 404
        assert foreign.json() == missing.json()
    for params in ({"limit": 0}, {"limit": 101}, {"surface": "anything"}):
        assert (await client.get("/api/answers", params=params)).status_code == 422
    assert fake_local.calls == []
    for table in (ModelCall, LearningEvent):
        assert await db.scalar(select(func.count()).select_from(table)) == 0


async def test_search_literal_words_owner_filters_and_index_lifecycle(
    client: AsyncClient, db: AsyncSession, fake_local: FakeProvider
) -> None:
    from sqlalchemy import delete, text, update

    owner = (await client.get("/api/learner/me")).json()["id"]
    other = LearnerProfile(display_name="Other")
    db.add(other)
    await db.commit()
    for id_, learner, answer in [
        ("10", owner, "Über cleaning groups"),
        ("11", owner, "Cleaning alone"),
        ("12", other.id, "Über cleaning groups"),
    ]:
        db.add(
            TutorAnswer(
                id=id_,
                learner_id=learner,
                turn_id=id_,
                surface="playground",
                request_json={"question": "Compare representation", "code": "secret_code_marker"},
                text=answer,
                metadata_json={},
                fingerprint=id_,
            )
        )
    await db.commit()

    async def results(query: str) -> list[str]:
        response = await client.get("/api/answers", params={"q": query})
        assert response.status_code == 200
        return [row["id"] for row in response.json()["items"]]

    assert await results("ÜBER groups") == ["10"]
    assert await results("representation") == ["11", "10"]
    assert await results("secret_code_marker") == []
    assert await results('" OR *') == []
    assert await results("***") == []
    assert (await client.get("/api/answers", params={"q": "cleaning", "surface": "tutor"})).json()[
        "items"
    ] == []
    page = (await client.get("/api/answers", params={"q": "cleaning", "limit": 1})).json()
    assert page["next_cursor"] == "11"
    assert (await client.get("/api/answers", params={"q": "cleaning", "cursor": "11"})).json()[
        "items"
    ][0]["id"] == "10"
    await db.execute(update(TutorAnswer).where(TutorAnswer.id == "10").values(text="Replacement"))
    await db.commit()
    assert await results("groups") == []
    await db.execute(delete(TutorAnswer).where(TutorAnswer.id == "11"))
    await db.commit()
    assert await results("cleaning") == []
    assert await db.scalar(text("SELECT count(*) FROM tutor_answer_fts WHERE id='11'")) == 0
    assert (await client.get("/api/answers", params={"q": "x" * 201})).status_code == 422
    assert fake_local.calls == []
