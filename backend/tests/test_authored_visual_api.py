import pytest
from sqlalchemy import func, select

from app.db.models import AuthoredVisualDocument, LearnerProfile, LearningEvent, ModelCall
from tests.test_authored_visual_commands import ask_spec, review_command, save_command


async def post(client, body, key="save"):
    return await client.post(
        "/api/authored-visuals/commands", json=body, headers={"Idempotency-Key": key}
    )


async def test_commands_save_retry_review_archive_restore(client, db, learner):
    spec = await ask_spec(db, learner)
    body = save_command(spec)
    first = await post(client, body)
    assert first.status_code == 200, first.text
    assert (await post(client, body)).json() == first.json()
    from app.schemas.authored_visuals import VisualReceipt

    receipt = VisualReceipt.model_validate(first.json())
    reviewed = await post(client, review_command(receipt), "review")
    assert reviewed.status_code == 200, reviewed.text
    archive = {
        "action": "archive",
        "document_id": receipt.document_id,
        "expected_revision": 2,
        "archived": True,
    }
    assert (await post(client, archive, "archive")).json()["archived"] is True
    archive.update(expected_revision=3, archived=False)
    assert (await post(client, archive, "restore")).json()["archived"] is False
    # A replay stays historical; it must never imply current revision/acceptance.
    assert (await post(client, body)).json()["revision"] == 1
    assert await db.scalar(select(func.count()).select_from(LearningEvent)) == 0
    assert await db.scalar(select(func.count()).select_from(ModelCall)) == 0


async def test_command_conflict_and_foreign_target(client, db, learner):
    spec = await ask_spec(db, learner)
    first = await post(client, save_command(spec))
    changed = save_command({**spec, "title": "Different"})
    assert (await post(client, changed)).status_code == 409
    other = LearnerProfile(display_name="Other")
    db.add(other)
    await db.commit()
    from app.api.deps import get_learner

    async def other_owner():
        return other

    app = client._transport.app
    app.dependency_overrides[get_learner] = other_owner
    try:
        response = await post(
            client,
            {
                "action": "archive",
                "document_id": first.json()["document_id"],
                "expected_revision": 1,
                "archived": True,
            },
            "foreign",
        )
        assert response.status_code == 404
        assert (await post(client, save_command(spec), "foreign-answer")).status_code == 409
    finally:
        del app.dependency_overrides[get_learner]


@pytest.mark.parametrize(
    "body",
    [b"{broken", b'{"private-secret":"sensitive"}', b'{"action":"save","origin":{"kind":"model"}}'],
)
async def test_invalid_payload_does_not_echo_input(client, db, learner, body):
    response = await client.post(
        "/api/authored-visuals/commands", content=body, headers={"Idempotency-Key": "invalid"}
    )
    assert response.status_code == 422
    assert "private-secret" not in response.text and "sensitive" not in response.text
    assert await db.scalar(select(func.count()).select_from(AuthoredVisualDocument)) == 0


async def test_stream_size_limit_and_missing_key(client, learner):
    async def chunks():
        for _ in range(130):
            yield b" " * 1024

    response = await client.post(
        "/api/authored-visuals/commands", content=chunks(), headers={"Idempotency-Key": "large"}
    )
    assert response.status_code == 413
    assert (await client.post("/api/authored-visuals/commands", json={})).status_code == 422
