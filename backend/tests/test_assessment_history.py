from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from app.db import models
from app.kernel.seed import load_seed
from app.models_ai import registry
from app.orchestrator import assessment_answers

SEED = Path(__file__).resolve().parents[2] / "seeds" / "attention"


async def prepare(client, db):
    await load_seed(db, SEED)
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    item = (await client.get("/api/assess/next", params={"session_id": session["id"]})).json()[
        "item"
    ]
    return session, item


@pytest.mark.parametrize("endpoint", ["/api/assess/attempt", "/api/challenge/submit"])
async def test_saved_grading_history_is_snapshot_not_new_evidence(client, db, fake_local, endpoint):
    session, item = await prepare(client, db)
    response = await client.post(
        endpoint,
        json={
            "content_version": item["content_version"],
            "session_id": session["id"],
            "assessment_id": item["id"],
            "answer": "0",
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["answer_id"] and not result["save_error"]
    tables = (
        models.AssessmentAttempt,
        models.CompetencyEvidence,
        models.LearningEvent,
        models.ModelCall,
    )
    counts = [await db.scalar(select(func.count()).select_from(t)) for t in tables]
    question = await db.get(models.Assessment, item["id"])
    question.item_json = {**question.item_json, "question": "Changed question"}
    await db.commit()
    for _ in range(2):
        detail = (await client.get("/api/answers/" + result["answer_id"])).json()
        assert detail["request"]["text"] == item["question"]
        assert detail["request"]["learner_answer"] == "0"
        assert detail["request"]["learner_answer_display"] == item["options"][0]
        assert detail["metadata"]["assessment_result"]["attempt_id"] == result["attempt_id"]
        assert detail["metadata"]["assessment_question"] == item
        assert detail["text"] == result["feedback"] + "\n\n" + result["next_step"]
    history = (await client.get("/api/answers", params={"surface": "assessment"})).json()
    assert len(history["items"]) == 1
    suggestions = (
        await client.get("/api/answers", params={"suggestions": "true", "surface": "assessment"})
    ).json()
    assert suggestions["items"] == []
    assert counts == [await db.scalar(select(func.count()).select_from(t)) for t in tables]
    assert fake_local.calls == []


@pytest.mark.parametrize("committed", [False, True])
async def test_retry_feedback_save_never_regrades(client, db, monkeypatch, committed):
    session, item = await prepare(client, db)
    original = assessment_answers.save_completed

    async def fail(connection, **snapshot):
        if committed:
            await original(connection, **snapshot)
        raise OperationalError("insert", {}, Exception("temporary"))

    monkeypatch.setattr(assessment_answers, "save_completed", fail)
    response = await client.post(
        "/api/assess/attempt",
        json={
            "content_version": item["content_version"],
            "session_id": session["id"],
            "assessment_id": item["id"],
            "answer": "0",
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["save_error"] and result["save_receipt"] and result["attempt_id"]
    counts = [
        await db.scalar(select(func.count()).select_from(t))
        for t in (models.AssessmentAttempt, models.CompetencyEvidence, models.LearningEvent)
    ]
    for _ in range(2):
        saved = await client.post(
            "/api/answers/recover-save", json={"receipt": result["save_receipt"]}
        )
        assert saved.status_code == 200, saved.text
    assert await db.scalar(select(func.count()).select_from(models.TutorAnswer)) == 1
    assert counts == [
        await db.scalar(select(func.count()).select_from(t))
        for t in (models.AssessmentAttempt, models.CompetencyEvidence, models.LearningEvent)
    ]


async def test_empty_feedback_keeps_grading_result_without_history_error(client, db):
    from app.schemas.grading import AttemptRequest, AttemptResult

    session, item = await prepare(client, db)
    request = AttemptRequest(
        session_id=session["id"],
        assessment_id=item["id"],
        content_version=item["content_version"],
        answer="0",
    )
    response = await client.post("/api/assess/attempt", json=request.model_dump())
    result = AttemptResult.model_validate(response.json()).model_copy(
        update={"feedback": "", "next_step": "", "answer_id": None}
    )
    attempt = await db.get(models.AssessmentAttempt, result.attempt_id)
    saved = await assessment_answers.save_feedback(
        db,
        result,
        request,
        learner_id=attempt.learner_id,
        question=item,
        area_id=None,
        course_label=None,
        recovery=None,
    )
    assert saved.attempt_id == result.attempt_id and saved.score == result.score
    assert saved.save_error and saved.answer_id is None
    assert await db.scalar(select(func.count()).select_from(models.TutorAnswer)) == 1
