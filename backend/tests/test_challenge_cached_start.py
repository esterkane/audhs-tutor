"""Opening a saved challenge must not depend on an installed embedding model."""

from unittest.mock import AsyncMock

import pytest

from app.core.errors import AppError
from app.db import models
from tests.test_exercises import _node
from tests.test_question_selection import suspend


@pytest.mark.parametrize("saved,excluded", [(True, False), (True, True), (False, False)])
async def test_challenge_checks_saved_identity_before_retrieval(
    client, db, monkeypatch, saved, excluded
):
    node = await _node(db)
    session = (await client.post("/api/sessions", json={"mode": "novelty", "energy": 3})).json()
    owner = await db.get(models.Session, session["id"])
    assessment = None
    if saved:
        assessment = models.Assessment(
            skill_id=node.id,
            kind="challenge_planted_error",
            item_json={
                "prompt": "Synthetic saved question",
                "hidden_key": "Private answer",
                "criteria": ["Find the error"],
                "sources": [],
            },
        )
        db.add(assessment)
        await db.commit()
        if excluded:
            await suspend(db, owner.learner_id, assessment.id)
    client._transport.app.state.repo = None
    build = AsyncMock(side_effect=AppError("no_model_ready", "No embedder installed", 503))
    monkeypatch.setattr("app.knowledge.reindex.build_repo", build)
    response = await client.post(
        "/api/challenge/start",
        json={
            "session_id": session["id"],
            "skill_id": node.id,
            "mode": "planted_error",
        },
    )
    if saved:
        assert response.status_code == (409 if excluded else 200), response.text
        build.assert_not_awaited()
        if not excluded:
            content = response.json()
            assert content["cached"] is True
            assert content["assessment_id"] == assessment.id
            assert content["prompt"] == "Synthetic saved question"
            assert "Private answer" not in response.text
            view = await client.get(f"/api/assess/items/{assessment.id}?session_id={session['id']}")
            assert view.json()["content_version"] == content["content_version"]
    else:
        assert response.status_code == 503
        build.assert_awaited_once()
