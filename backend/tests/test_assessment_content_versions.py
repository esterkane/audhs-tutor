"""Content changes never silently alter the work graded or committed."""

import hashlib
import json
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.db import models
from app.kernel.seed import load_seed
from app.models_ai import registry
from app.orchestrator import assessment_content
from app.orchestrator.grader import Grader
from app.schemas.grading import AttemptRequest, CriterionResult, GradeResult

SEED = Path(__file__).resolve().parents[2] / "seeds" / "attention"
KEY = "82b914ea-2562-4e73-821e-f25431583c87"


async def prepare(client, db):
    await load_seed(db, SEED)
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    item = (await client.get("/api/assess/next", params={"session_id": session["id"]})).json()[
        "item"
    ]
    return {
        "session_id": session["id"],
        "assessment_id": item["id"],
        "content_version": item["content_version"],
        "answer": "0",
    }


@pytest.mark.parametrize("field", ["question", "answer", "rubric"])
async def test_stale_new_claim_rejected_before_model_or_evidence(client, db, fake_local, field):
    body = await prepare(client, db)
    a = await db.get(models.Assessment, body["assessment_id"])
    if field == "rubric":
        rubric = models.AssessmentRubric(
            criteria_json=[{"criterion": "Changed", "keywords": []}], version=1
        )
        db.add(rubric)
        await db.flush()
        a.rubric_id = rubric.id
    else:
        a.item_json = {**a.item_json, field: "Changed prompt" if field == "question" else 1}
    await db.commit()
    reply = await client.post("/api/assess/attempt", json=body, headers={"Idempotency-Key": KEY})
    assert reply.status_code == 409
    assert reply.json()["error"]["code"] == "assessment_content_changed"
    for table in [models.AssessmentAttempt, models.CompetencyEvidence, models.WorkspaceRequest]:
        assert await db.scalar(select(func.count()).select_from(table)) == 0
    assert not fake_local.calls
    refreshed = await client.get(
        "/api/assess/items/" + a.id, params={"session_id": body["session_id"]}
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["content_version"] != body["content_version"]


async def test_missing_token_rejected_but_completed_legacy_replay_survives_changes(client, db):
    body = await prepare(client, db)
    body.pop("content_version")
    rejected = await client.post("/api/assess/attempt", json=body)
    assert rejected.json()["error"]["code"] == "assessment_content_required"
    # Simulate a completed pre-token claim using its original canonical payload shape.
    req = AttemptRequest(**body)
    result = await Grader(db, None).grade(req)
    payload = req.model_dump(mode="json")
    payload.pop("content_version")
    session = await db.get(models.Session, body["session_id"])
    db.add(
        models.WorkspaceRequest(
            learner_id=session.learner_id,
            session_id=session.id,
            request_key="assessment:" + KEY,
            fingerprint=hashlib.sha256(
                json.dumps(
                    payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                ).encode()
            ).hexdigest(),
            response_json=result.model_dump(mode="json"),
        )
    )
    a = await db.get(models.Assessment, body["assessment_id"])
    a.item_json = {**a.item_json, "question": "Now changed"}
    await db.commit()
    replay = await client.post("/api/assess/attempt", json=body, headers={"Idempotency-Key": KEY})
    assert replay.status_code == 200, replay.text
    assert replay.json()["attempt_id"] == result.attempt_id
    assert await db.scalar(select(func.count()).select_from(models.AssessmentAttempt)) == 1


async def test_rubric_edit_during_inference_rejects_learning_commit(
    client, db, monkeypatch, session_factory
):
    body = await prepare(client, db)
    a = await db.get(models.Assessment, body["assessment_id"])
    rubric = models.AssessmentRubric(
        criteria_json=[{"criterion": "Explain", "keywords": []}], version=1
    )
    db.add(rubric)
    await db.flush()
    a.kind = "explain_back"
    a.rubric_id = rubric.id
    a.item_json = {"prompt": "Explain this", "expected_answer": "Reference"}
    await db.commit()
    body["content_version"] = assessment_content.token(await assessment_content.snapshot(db, a.id))
    body["answer"] = "My explanation"

    async def changed(self, *args, **kwargs):
        async with session_factory() as other:
            r = await other.get(models.AssessmentRubric, rubric.id)
            r.criteria_json = [
                {"criterion": "Different rubric without version increment", "keywords": []}
            ]
            await other.commit()
        return GradeResult(
            criterion_results=[CriterionResult(criterion="Explain", passed=True)],
            confidence=1,
            feedback="Synthetic",
            next_step="Continue",
        ), "local"

    monkeypatch.setattr(Grader, "_llm_grade", changed)
    reply = await client.post("/api/assess/attempt", json=body, headers={"Idempotency-Key": KEY})
    assert reply.status_code == 409, reply.text
    assert reply.json()["error"]["code"] == "assessment_content_changed_during_grading"
    assert await db.scalar(select(func.count()).select_from(models.AssessmentAttempt)) == 0
    assert await db.scalar(select(func.count()).select_from(models.CompetencyEvidence)) == 0
    claim = await db.scalar(select(models.WorkspaceRequest))
    assert claim.response_json is None


async def test_completed_versioned_replay_survives_restart_and_hidden_key_edit(
    client, db, monkeypatch
):
    body = await prepare(client, db)
    headers = {"Idempotency-Key": KEY}
    first = await client.post("/api/assess/attempt", json=body, headers=headers)
    assert first.status_code == 200
    a = await db.get(models.Assessment, body["assessment_id"])
    a.item_json = {**a.item_json, "answer": 1}
    await db.commit()
    from app.core import content_versions

    monkeypatch.setattr(content_versions, "_KEY", b"different-process-key")
    replay = await client.post("/api/assess/attempt", json=body, headers=headers)
    assert replay.status_code == 200
    assert replay.json() == first.json()
    assert await db.scalar(select(func.count()).select_from(models.AssessmentAttempt)) == 1


async def test_hidden_reference_changes_token_without_echoing_content(client, db):
    body = await prepare(client, db)
    original = await assessment_content.snapshot(db, body["assessment_id"])
    modified = {**original, "item_json": {**original["item_json"], "hidden_key": "PRIVATE_KEY"}}
    assert assessment_content.token(original) != assessment_content.token(modified)
    assert "PRIVATE" not in assessment_content.token(modified)


async def test_concurrent_completed_claim_beats_stale_new_validation(client, db, session_factory):
    """A waiting same-key submission replays instead of claiming no grading occurred."""
    import asyncio

    from app.db import workspace_requests

    body = await prepare(client, db)
    session = await db.get(models.Session, body["session_id"])
    learner_id, session_id = session.learner_id, session.id
    await db.commit()
    entered, proceed = asyncio.Event(), asyncio.Event()
    second_validated = []
    async with session_factory() as first, session_factory() as second:

        async def hold_validation():
            entered.set()
            await proceed.wait()

        first_task = asyncio.create_task(
            workspace_requests.claim(
                first,
                learner_id,
                session_id,
                "assessment:" + KEY,
                body,
                validate_new=hold_validation,
            )
        )
        await entered.wait()

        async def stale_validation():
            second_validated.append(True)
            await assessment_content.validate_new(second, body["assessment_id"], "stale")

        second_task = asyncio.create_task(
            workspace_requests.claim(
                second,
                learner_id,
                session_id,
                "assessment:" + KEY,
                body,
                validate_new=stale_validation,
            )
        )
        # Complete inside first claim transaction before releasing its lock.
        # The validator models another caller's finished row becoming visible.
        import hashlib
        import json

        from app.db.models import WorkspaceRequest

        first.add(
            WorkspaceRequest(
                learner_id=learner_id,
                session_id=session_id,
                request_key="assessment:" + KEY,
                fingerprint=hashlib.sha256(
                    json.dumps(
                        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                    ).encode()
                ).hexdigest(),
                response_json={"completed": "original"},
            )
        )
        changed = await first.get(models.Assessment, body["assessment_id"])
        changed.item_json = {**changed.item_json, "question": "Concurrent revised content"}
        await first.flush()
        proceed.set()
        _, first_result = await first_task
        _, second_result = await second_task
    assert first_result == second_result == {"completed": "original"}
    assert second_validated == []
