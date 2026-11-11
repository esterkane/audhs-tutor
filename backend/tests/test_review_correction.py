from uuid import uuid4

import pytest

from app.db.models import Assessment, AssessmentAttempt, Session
from tests.test_assessment_requests import prepare
from tests.test_assessment_revisions import learning_rows


@pytest.mark.parametrize(
    "negative", ["low-confidence", "ungraded", "old-content", "unlinked", "later-failure"]
)
async def test_only_current_qualified_correction_is_shown(client, db, negative):
    body = await prepare(client, db)
    item = await db.get(Assessment, body["assessment_id"])
    answer = item.item_json["answer"]
    options = item.item_json["options"]
    wrong = (answer + 1) % len(options)
    original = (
        await client.post(
            "/api/assess/attempt",
            json=body | {"answer": str(wrong), "confidence_pre": 4},
            headers={"Idempotency-Key": str(uuid4())},
        )
    ).json()
    revision = (
        await client.post(
            "/api/assess/attempt",
            json=body | {"answer": str(answer), "revision_of_attempt_id": original["attempt_id"]},
            headers={"Idempotency-Key": str(uuid4())},
        )
    ).json()
    root = await db.get(AssessmentAttempt, original["attempt_id"])
    corrected = await db.get(AssessmentAttempt, revision["attempt_id"])
    previous_session = await db.get(Session, root.session_id)
    previous_session.ended_at = corrected.ts
    await db.commit()
    later = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    item_url = "/api/review/items/" + original["review"]["item_id"]
    card = (await client.get(item_url, params={"session_id": later["id"]})).json()

    async def lookup():
        res = await client.get(
            item_url + "/correction",
            params={"session_id": later["id"], "content_version": card["content_version"]},
        )
        assert res.status_code == 200, res.text
        return res.json()

    before = await learning_rows(db)
    assert await lookup() == {"earlier": options[wrong], "corrected": options[answer]}
    if negative == "low-confidence":
        root.confidence_pre = 3
    elif negative == "ungraded":
        corrected.grader_route = "rubric"
    elif negative == "old-content":
        corrected.content_fingerprint = None
    elif negative == "unlinked":
        corrected.revision_of_attempt_id = None
    elif negative == "later-failure":
        corrected.correct = False
    await db.commit()
    assert await lookup() is None
    assert await learning_rows(db) == before
