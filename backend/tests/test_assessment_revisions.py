import pytest

from app.core.errors import AppError
from app.db.models import Assessment, AssessmentAttempt, LearnerProfile, Session
from app.orchestrator.assessment_revisions import validate_root
from tests.test_assessment_requests import HEADERS, counts, prepare


async def original(client, db):
    body = await prepare(client, db)
    response = await client.post("/api/assess/attempt", json=body, headers=HEADERS)
    assert response.status_code == 200, response.text
    root = await db.get(AssessmentAttempt, response.json()["attempt_id"])
    args = dict(
        learner_id=root.learner_id,
        session_id=body["session_id"],
        assessment_id=body["assessment_id"],
        root_attempt_id=root.id,
    )
    return root, args


async def test_root_validation_is_read_only_and_survives_reopening(client, db, session_factory):
    root, args = await original(client, db)
    assert root.content_fingerprint.startswith("assessment-recovery-v1:")
    before = await counts(db)
    async with session_factory() as reopened:
        assert (await validate_root(reopened, **args)).id == root.id
    assert await counts(db) == before


@pytest.mark.parametrize(
    "case,code",
    [
        ("foreign", "revision_original_unavailable"),
        ("wrong_session", "revision_original_unavailable"),
        ("missing", "revision_original_unavailable"),
        ("wrong_item", "revision_original_unavailable"),
        ("legacy", "revision_original_unverified"),
        ("revision", "revision_original_required"),
        ("changed", "revision_content_changed"),
        ("ended", "revision_session_ended"),
    ],
)
async def test_invalid_roots_are_not_graded(client, db, fake_local, case, code):
    root, args = await original(client, db)
    if case == "foreign":
        other = LearnerProfile(display_name="Other")
        db.add(other)
        await db.flush()
        root.learner_id = other.id
    if case == "wrong_session":
        root.session_id = None
    if case == "missing":
        args["root_attempt_id"] = "missing"
    if case == "wrong_item":
        args["assessment_id"] = "another"
    if case == "legacy":
        root.content_fingerprint = None
    if case == "revision":
        root.revision_of_attempt_id = root.id
    if case == "changed":
        item = await db.get(Assessment, root.assessment_id)
        item.item_json = {**item.item_json, "question": "Changed wording"}
    if case == "ended":
        session = await db.get(Session, root.session_id)
        session.ended_at = "2026-10-11T00:00:00Z"
    await db.commit()
    before = await counts(db)
    with pytest.raises(AppError) as exc:
        await validate_root(db, **args)
    assert exc.value.code == code
    assert await counts(db) == before
    assert fake_local.calls == []


async def test_revalidation_observes_external_session_end(client, db, session_factory):
    _, args = await original(client, db)
    held = await db.get(Session, args["session_id"])
    await validate_root(db, **args)
    await db.commit()  # inference runs without a database read transaction
    async with session_factory() as other:
        row = await other.get(Session, args["session_id"])
        row.ended_at = "2026-10-11T00:00:00Z"
        await other.commit()
    assert held.ended_at is None  # identity-map state was not implicitly refreshed
    with pytest.raises(AppError) as exc:
        await validate_root(db, **args)
    assert exc.value.code == "revision_session_ended"


async def learning_rows(db):
    from sqlalchemy import text

    return {
        table: list((await db.execute(text(f"SELECT * FROM {table} ORDER BY id"))).all())
        for table in ["competency_evidence", "competency_state", "memory_state", "review_item"]
    }


@pytest.mark.parametrize("explicit", [True, False])
async def test_revision_records_new_answer_without_reapplying_learning(
    client, db, fake_local, explicit
):
    from uuid import uuid4

    from sqlalchemy import select

    from app.db.models import TutorAnswer

    root, args = await original(client, db)
    before = await learning_rows(db)
    original_answer = root.answer
    # Next may rotate, so derive this exact root's current view without altering it.
    from app.orchestrator.grader import versioned_view

    original_item = await db.get(Assessment, root.assessment_id)
    item = await versioned_view(db, original_item, root.learner_id)
    body = dict(
        session_id=args["session_id"],
        assessment_id=root.assessment_id,
        content_version=item.content_version,
        answer="1",
        revision_of_attempt_id=root.id,
    )
    if not explicit:
        body.pop("revision_of_attempt_id")
    headers = {"Idempotency-Key": str(uuid4())}
    response = await client.post("/api/assess/attempt", json=body, headers=headers)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["revision_of_attempt_id"] == root.id
    assert result["review_updated"] is False
    assert result["attempt_id"] != root.id
    assert await learning_rows(db) == before
    revision = await db.get(AssessmentAttempt, result["attempt_id"])
    assert revision.answer == "1" and revision.revision_of_attempt_id == root.id
    await db.refresh(root)
    assert root.answer == original_answer and root.revision_of_attempt_id is None
    saved = await db.scalar(select(TutorAnswer).where(TutorAnswer.id == result["answer_id"]))
    assert "Repeated practice on a previously checked question" in saved.text
    totals = await counts(db)
    replay = await client.post("/api/assess/attempt", json=body, headers=headers)
    assert replay.json() == result
    assert await counts(db) == totals
    assert await learning_rows(db) == before
    # A further revision uses the original root; a revision cannot become a root.
    invalid = await client.post(
        "/api/assess/attempt",
        json={**body, "revision_of_attempt_id": revision.id},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert invalid.status_code == 409
    assert await counts(db) == totals
    again = await client.post(
        "/api/assess/attempt",
        json={**body, "answer": "0"},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert again.status_code == 200, again.text
    assert await learning_rows(db) == before
    session = await db.get(Session, root.session_id)
    session.ended_at = "2026-10-11T00:00:00Z"
    await db.commit()
    replay = await client.post("/api/assess/attempt", json=body, headers=headers)
    assert replay.json() == result
    rejected = await client.post(
        "/api/assess/attempt", json=body, headers={"Idempotency-Key": str(uuid4())}
    )
    assert rejected.status_code >= 400
    assert await learning_rows(db) == before
    assert fake_local.calls == []


@pytest.mark.parametrize("explicit", [True, False])
async def test_revision_commit_failure_finishes_once_after_session_end(
    client, db, monkeypatch, explicit
):
    from uuid import uuid4

    from app.db import workspace_requests
    from app.orchestrator.grader import versioned_view

    root, args = await original(client, db)
    item = await versioned_view(db, await db.get(Assessment, root.assessment_id), root.learner_id)
    body = dict(
        session_id=args["session_id"],
        assessment_id=root.assessment_id,
        content_version=item.content_version,
        answer="1",
        revision_of_attempt_id=root.id,
    )
    if not explicit:
        body.pop("revision_of_attempt_id")
    identity = str(uuid4())
    before = await learning_rows(db)
    totals = await counts(db)
    complete = workspace_requests.complete

    async def fail(*args, **kwargs):
        await complete(*args, **kwargs)
        raise RuntimeError("revision commit interrupted")

    with monkeypatch.context() as patch:
        patch.setattr(workspace_requests, "complete", fail)
        with pytest.raises(RuntimeError, match="revision commit interrupted"):
            await client.post(
                "/api/assess/attempt", json=body, headers={"Idempotency-Key": identity}
            )
    assert await counts(db) == totals
    assert await learning_rows(db) == before
    session = await db.get(Session, args["session_id"])
    session.ended_at = "2026-10-11T00:00:00Z"
    await db.commit()
    path = f"/api/assess/requests/{identity}"
    assert (await client.get(path, params={"session_id": session.id})).json()[
        "status"
    ] == "grade_ready"
    finished = await client.post(path + "/finish", params={"session_id": session.id})
    assert finished.status_code == 200, finished.text
    assert finished.json()["revision_of_attempt_id"] == root.id
    assert finished.json()["review_updated"] is False
    assert await learning_rows(db) == before
    after = await counts(db)
    replay = await client.post(path + "/finish", params={"session_id": session.id})
    assert replay.json() == finished.json()
    assert await counts(db) == after
    assert await learning_rows(db) == before


async def test_later_session_is_an_ordinary_attempt(client, db):
    from uuid import uuid4

    from app.orchestrator.grader import versioned_view

    root, args = await original(client, db)
    old = await db.get(Session, args["session_id"])
    old.ended_at = "2026-10-11T00:00:00Z"
    await db.commit()
    new = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    item = await versioned_view(db, await db.get(Assessment, root.assessment_id), root.learner_id)
    before = await counts(db)
    response = await client.post(
        "/api/assess/attempt",
        json={
            "session_id": new["id"],
            "assessment_id": root.assessment_id,
            "content_version": item.content_version,
            "answer": "0",
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 200, response.text
    assert response.json()["revision_of_attempt_id"] is None
    assert response.json()["review_updated"] is True
    assert (await counts(db))[1] == before[1] + 1


async def test_concurrent_new_identities_share_one_original(client, db, monkeypatch):
    import asyncio
    from uuid import uuid4

    from sqlalchemy import select

    from app.orchestrator.grader import Grader

    body = await prepare(client, db)
    apply = Grader.apply_result
    entered = 0
    ready = asyncio.Event()

    async def together(self, *args, **kwargs):
        nonlocal entered
        entered += 1
        if entered == 2:
            ready.set()
        await asyncio.wait_for(ready.wait(), 5)
        return await apply(self, *args, **kwargs)

    monkeypatch.setattr(Grader, "apply_result", together)
    responses = await asyncio.gather(
        *[
            client.post("/api/assess/attempt", json=body, headers={"Idempotency-Key": str(uuid4())})
            for _ in range(2)
        ]
    )
    assert all(r.status_code == 200 for r in responses), [r.text for r in responses]
    results = [r.json() for r in responses]
    original_result = next(r for r in results if r["revision_of_attempt_id"] is None)
    revision = next(r for r in results if r["revision_of_attempt_id"] is not None)
    assert revision["revision_of_attempt_id"] == original_result["attempt_id"]
    assert revision["review_updated"] is False
    assert (await counts(db))[1] == 1
    attempts = list((await db.scalars(select(AssessmentAttempt))).all())
    assert len(attempts) == 2
