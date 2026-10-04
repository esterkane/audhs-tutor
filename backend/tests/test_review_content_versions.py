"""Review evidence is tied to the exact displayed content, not its mutable ID."""

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.db import models, workspace_requests
from app.kernel import memory
from app.kernel.seed import load_seed

SEED = Path(__file__).resolve().parents[2] / "seeds" / "attention"


async def prepare(client, db, *, assessment=False):
    await load_seed(db, SEED)
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    owner = await db.get(models.Session, session["id"])
    node = await db.scalar(select(models.SkillNode))
    source = await db.scalar(select(models.Assessment).where(models.Assessment.kind == "mcq"))
    prompt = (
        {"assessment_id": "", "ref": source.id}
        if assessment
        else {"type": "vocab", "q": "word", "a": "meaning"}
    )
    item, _ = await memory.ensure_item(
        db, owner.learner_id, node.id, "mcq" if assessment else "vocab", prompt
    )
    shown = (
        await client.get(f"/api/review/items/{item.id}", params={"session_id": session["id"]})
    ).json()
    return (
        item,
        source,
        {"session_id": session["id"], "rating": 4, "content_version": shown["content_version"]},
        shown,
    )


async def count(db, cls):
    return await db.scalar(select(func.count()).select_from(cls))


@pytest.mark.parametrize("change", ["missing", "meaning", "answer", "unicode"])
async def test_stale_new_rating_never_claims_or_changes_schedule(client, db, change):
    item, source, body, shown = await prepare(client, db, assessment=change == "answer")
    before = list((await db.execute(select(models.MemoryState.__table__))).mappings())
    if change == "missing":
        body.pop("content_version")
    elif change == "unicode":
        body["content_version"] = "☃"
    elif change == "answer":
        assert (
            shown["question"] == source.item_json["question"]
        )  # empty assessment_id falls back to ref
        source.item_json = {
            **source.item_json,
            "answer": (int(source.item_json["answer"]) + 1) % len(source.item_json["options"]),
        }
    else:
        item.prompt_json = {**item.prompt_json, "a": "changed meaning"}
    await db.commit()
    response = await client.post(
        f"/api/review/{item.id}", json=body, headers={"Idempotency-Key": str(uuid4())}
    )
    assert response.status_code == 409
    assert await count(db, models.WorkspaceRequest) == 0
    assert await count(db, models.ReviewLog) == 0
    assert list((await db.execute(select(models.MemoryState.__table__))).mappings()) == before


async def test_completed_replay_survives_source_deletion_and_inactive_item(client, db):
    item, source, body, _ = await prepare(client, db, assessment=True)
    headers = {"Idempotency-Key": str(uuid4())}
    first = await client.post(f"/api/review/{item.id}", json=body, headers=headers)
    assert first.status_code == 200
    await db.delete(source)
    item.active = False
    await db.commit()
    again = await client.post(f"/api/review/{item.id}", json=body, headers=headers)
    assert again.json() == first.json()
    assert await count(db, models.ReviewLog) == 1
    assert (
        await client.get(f"/api/review/items/{item.id}", params={"session_id": body["session_id"]})
    ).status_code == 404


async def test_final_guard_rejects_edit_after_claim_without_review_evidence(
    client, db, session_factory, monkeypatch
):
    item, _, body, _ = await prepare(client, db)
    original = workspace_requests.claim

    async def edited(*args, **kwargs):
        result = await original(*args, **kwargs)
        # Simulate an accidental same-transaction edit. External writers are now
        # serialized outside the entire claim/rating transaction.
        writer = args[0]
        row = await writer.get(models.ReviewItem, item.id)
        row.prompt_json = {**row.prompt_json, "a": "new meaning"}
        await writer.flush()
        return result

    monkeypatch.setattr(workspace_requests, "claim", edited)
    response = await client.post(
        f"/api/review/{item.id}", json=body, headers={"Idempotency-Key": str(uuid4())}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "review_content_changed_during_rating"
    assert await count(db, models.ReviewLog) == 0
    assert await db.scalar(select(models.WorkspaceRequest)) is None


async def test_schedule_change_does_not_change_content_token(client, db):
    item, _, body, _ = await prepare(client, db)
    first = await client.post(f"/api/review/{item.id}", json=body)
    assert first.status_code == 200
    shown = (
        await client.get(f"/api/review/items/{item.id}", params={"session_id": body["session_id"]})
    ).json()
    assert shown["content_version"] == body["content_version"]


async def test_rubric_change_invalidates_even_if_display_unchanged(client, db):
    item, source, body, _ = await prepare(client, db, assessment=True)
    rubric = models.AssessmentRubric(criteria_json=[{"criterion": "hidden criterion"}])
    db.add(rubric)
    await db.flush()
    source.rubric_id = rubric.id
    await db.commit()
    shown = (
        await client.get(f"/api/review/items/{item.id}", params={"session_id": body["session_id"]})
    ).json()
    body["content_version"] = shown["content_version"]
    rubric.criteria_json = [{"criterion": "changed hidden criterion"}]
    await db.commit()
    response = await client.post(
        f"/api/review/{item.id}", json=body, headers={"Idempotency-Key": str(uuid4())}
    )
    assert response.status_code == 409
    assert await count(db, models.WorkspaceRequest) == 0
    assert await count(db, models.ReviewLog) == 0


async def test_completed_legacy_payload_replays_without_version(client, db):
    import hashlib
    import json

    from app.schemas.review import ReviewRating

    item, _, body, _ = await prepare(client, db)
    key = str(uuid4())
    headers = {"Idempotency-Key": key}
    first = await client.post(f"/api/review/{item.id}", json=body, headers=headers)
    assert first.status_code == 200
    body.pop("content_version")
    old_body = ReviewRating.model_validate(body).model_dump(mode="json")
    old_body.pop("content_version")
    payload = {"item_id": item.id, "body": old_body, "as_of": None}
    claim = await db.scalar(select(models.WorkspaceRequest))
    claim.fingerprint = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    item.prompt_json = {**item.prompt_json, "a": "changed"}
    await db.commit()
    assert (
        await client.post(f"/api/review/{item.id}", json=body, headers=headers)
    ).json() == first.json()
    assert await count(db, models.ReviewLog) == 1
