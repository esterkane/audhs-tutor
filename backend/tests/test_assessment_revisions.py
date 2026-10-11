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
