"""Streaming is a transport change, not new feedback or learning evidence."""

import json
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.db.models import AssessmentAttempt, LearnerProfile, ModelCall, TutorAnswer
from app.models_ai.registry import seed_defaults


def events(response):
    return [
        (block.split("\n")[0][7:], json.loads(block.split("data: ")[1]))
        for block in response.text.strip().split("\n\n")
    ]


@pytest.mark.parametrize("purpose", ["followup", "correction"])
async def test_followup_stream_keeps_context_identity_ownership_and_evidence(
    client, db, fake_local, purpose
):
    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "gemma3:12b"})
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    owner = (await client.get("/api/learner/me")).json()["id"]
    other = LearnerProfile(display_name="Other")
    db.add(other)
    await db.commit()
    for identifier, learner in [("parent", owner), ("foreign", other.id)]:
        db.add(
            TutorAnswer(
                id=identifier,
                learner_id=learner,
                turn_id=identifier,
                surface="assessment",
                request_json={
                    "question": "What is 2+3?",
                    "learner_answer": "0",
                    "learner_answer_display": "4",
                },
                text="Compare the sum again.",
                metadata_json={"assessment_question": {"kind": "mcq"}},
                fingerprint=identifier,
            )
        )
    await db.commit()
    await client.put(
        "/api/answers/parent/feedback", json={"verdict": "incorrect", "note": "Explain why"}
    )
    fake_local.text = "Add two and three to get five."
    body = {"session_id": session["id"], "question": "Explain my answer.", "purpose": purpose}
    headers = {"Idempotency-Key": str(uuid4())}
    for identifier in ["foreign", "missing"]:
        response = await client.post(
            f"/api/answers/{identifier}/followup/stream", json=body, headers=headers
        )
        assert response.status_code == 404
    assert fake_local.calls == []
    response = await client.post("/api/answers/parent/followup/stream", json=body, headers=headers)
    assert response.status_code == 200
    chunks = events(response)
    assert chunks[0][0] == "token" and chunks[-1][0] == "done"
    final = chunks[-1][1]
    child = await db.get(TutorAnswer, final["answer_id"])
    assert child.metadata_json["parent_answer_id"] == "parent"
    assert child.metadata_json["followup_purpose"] == purpose
    assert child.request_json["historical_answer"]["learner_answer"] == "4"
    assert child.request_json["historical_answer"]["learner_report"]["note"] == "Explain why"
    assert (await db.get(TutorAnswer, "parent")).request_json["learner_answer"] == "0"
    # Both endpoints recover the same completed record without another model call.
    replay = await client.post("/api/answers/parent/followup", json=body, headers=headers)
    assert replay.json() == final
    replay_stream = await client.post(
        "/api/answers/parent/followup/stream", json=body, headers=headers
    )
    assert events(replay_stream) == [("done", final)]
    conflict = await client.post(
        "/api/answers/parent/followup/stream",
        json={**body, "question": "Different work"},
        headers=headers,
    )
    assert events(conflict)[-1][0] == "error"
    assert events(conflict)[-1][1]["code"] == "request_conflict"
    assert await db.scalar(select(func.count()).select_from(ModelCall)) == 1
    assert await db.scalar(select(func.count()).select_from(TutorAnswer)) == 3
    assert await db.scalar(select(func.count()).select_from(AssessmentAttempt)) == 0


@pytest.mark.parametrize("failure", ["partial", "length", "save"])
async def test_followup_failure_never_regenerates_or_loses_save_recovery(
    client, db, fake_local, monkeypatch, failure
):
    from sqlalchemy.exc import OperationalError

    from app.orchestrator import playground

    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "gemma3:12b"})
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    owner = (await client.get("/api/learner/me")).json()["id"]
    db.add(
        TutorAnswer(
            id="p",
            learner_id=owner,
            turn_id="p",
            surface="playground",
            request_json={"question": "Why?"},
            text="Previous explanation",
            metadata_json={},
            fingerprint="p",
        )
    )
    await db.commit()
    fake_local.text = "Compare these groups carefully."
    if failure == "partial":
        fake_local.fail_after_words = 1
    elif failure == "length":
        from app.models_ai.provider import StreamFinish

        original = fake_local.stream

        async def capped(*args, **kwargs):
            async for event in original(*args, **kwargs):
                yield event
            yield StreamFinish(reason="length")

        monkeypatch.setattr(fake_local, "stream", capped)
    else:

        async def fail(connection, **snapshot):
            await connection.rollback()
            raise OperationalError("insert", {}, Exception("temporary failure"))

        monkeypatch.setattr(playground, "save_completed", fail)
    body = {"session_id": session["id"], "question": "Explain again"}
    headers = {"Idempotency-Key": str(uuid4())}
    first = events(await client.post("/api/answers/p/followup/stream", json=body, headers=headers))
    assert first[0][0] == "token"
    calls = len(fake_local.calls)
    retry = events(await client.post("/api/answers/p/followup/stream", json=body, headers=headers))
    assert len(fake_local.calls) == calls == 1
    assert await db.scalar(select(func.count()).select_from(AssessmentAttempt)) == 0
    if failure in {"partial", "length"}:
        assert first[-1][0] == "error"
        if failure == "length":
            assert first[-1][1]["code"] == "tutor_output_limit"
        assert not any(kind == "done" for kind, _ in first)
        assert retry[-1][1]["code"] == "request_unresolved"
        assert await db.scalar(select(func.count()).select_from(TutorAnswer)) == 1
    else:
        final = first[-1][1]
        assert first[-1][0] == "done" and not final["answer_id"] and final["save_receipt"]
        assert retry == [("done", final)]
        saved = await client.post(
            "/api/answers/recover-save", json={"receipt": final["save_receipt"]}
        )
        assert saved.status_code == 200
        child = await db.get(TutorAnswer, saved.json()["answer_id"])
        assert child.text == final["text"]
        assert child.metadata_json["parent_answer_id"] == "p"
        assert await db.scalar(select(func.count()).select_from(TutorAnswer)) == 2
        assert len(fake_local.calls) == calls
