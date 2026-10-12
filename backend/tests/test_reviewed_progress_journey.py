"""Real HTTP/storage pipeline with synthetic grading, not model-quality evidence."""

from uuid import uuid4

import pytest

from tests.test_assessment_requests import counts, prepare
from tests.test_task_reviews import setup_task


@pytest.mark.parametrize("approve_before", [False, True])
async def test_review_answer_progress_replay_and_revocation(client, db, fake_local, approve_before):
    session_body = await prepare(client, db)
    task, _, skill = await setup_task(db)
    review_url = f"/api/questions/{task.id}/task-review"

    async def decision(action, revision):
        preview = await client.get(review_url)
        assert preview.status_code == 200, preview.text
        response = await client.post(
            review_url,
            json={
                "request_id": str(uuid4()),
                "expected_revision": revision,
                "content_version": preview.json()["content_version"],
                "decision": action,
                "facet": "explanation",
                "confirmed": True,
            },
        )
        assert response.status_code == 200, response.text

    if approve_before:
        await decision("approve", 0)
    fake_local.structured = {
        "criterion_results": [
            {
                "criterion": "Give a causal explanation",
                "passed": True,
                "evidence": "Removing incomplete rows excludes some groups.",
            }
        ],
        "confidence": 0.95,
        "feedback": "Synthetic causal explanation check.",
        "next_step": "Compare missingness across groups.",
    }
    view = await client.get(
        f"/api/assess/items/{task.id}", params={"session_id": session_body["session_id"]}
    )
    assert view.status_code == 200, view.text
    body = {
        "session_id": session_body["session_id"],
        "assessment_id": task.id,
        "content_version": view.json()["content_version"],
        "answer": "Removing incomplete rows excludes some groups.",
        "hint_count": 1,
    }
    headers = {"Idempotency-Key": str(uuid4())}
    result = await client.post("/api/assess/attempt", json=body, headers=headers)
    assert result.status_code == 200, result.text
    assert result.json()["score"] == 1
    assert len(fake_local.calls) == 1
    before = await counts(db)

    async def evidence():
        response = await client.get(f"/api/skills/{skill.id}/evidence")
        assert response.status_code == 200, response.text
        rows = response.json()["items"]
        assert rows and all(row["attempt_id"] == result.json()["attempt_id"] for row in rows)
        assert all(row["reported_hint_count"] == 1 for row in rows)
        return rows

    for row in await evidence():
        reviewed = row["reviewed_result"]
        if approve_before:
            assert reviewed["label"] == "Explanation check passed"
            assert reviewed["currently_eligible"]
            assert reviewed["grading_method"] == "local"
            assert reviewed["independence"] == "not_verified"
        else:
            assert reviewed is None
    # No retroactive qualification; revocation preserves historical checks.
    await decision("revoke" if approve_before else "approve", int(approve_before))
    for row in await evidence():
        reviewed = row["reviewed_result"]
        if approve_before:
            assert reviewed["label"] == "Explanation check passed"
            assert not reviewed["currently_eligible"] and reviewed["exclusion_reason"]
        else:
            assert reviewed is None
    replay = await client.post("/api/assess/attempt", json=body, headers=headers)
    assert replay.status_code == 200 and replay.json() == result.json()
    assert await counts(db) == before
    assert len(fake_local.calls) == 1
