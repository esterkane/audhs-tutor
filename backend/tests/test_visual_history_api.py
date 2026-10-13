import pytest
from sqlalchemy import delete, select

from app.api.deps import get_learner
from app.db.models import AuthoredVisualSourceSnapshot as Snapshot
from app.db.models import Chunk, ChunkProvenance, LearnerProfile, TutorAnswer
from app.schemas.authored_visuals import VisualReceipt
from tests.test_authored_visual_api import post
from tests.test_authored_visual_commands import ask_spec, review_command, save_command


async def setup(client, db, learner, sourced=False):
    response = await post(client, save_command(await ask_spec(db, learner, sourced)))
    assert response.status_code == 200, response.text
    receipt = VisualReceipt.model_validate(response.json())
    path = f"/api/authored-visuals/{receipt.document_id}/versions/{receipt.version_id}"
    return receipt, path


async def test_read_history_archive_and_current_revision(client, db, learner):
    receipt, path = await setup(client, db, learner)
    detail = (await client.get(path)).json()
    assert detail["grounding_now"] == "ungrounded"
    assert detail["origin"]["kind"] == "learner"
    assert detail["review_meaning"] == "historical_presentation_review_only"
    assert "snapshot_json" not in detail
    assert (await post(client, review_command(receipt), "review")).status_code == 200
    reviews = (await client.get(path + "/reviews")).json()
    assert reviews[0]["decision"] == "accept"
    assert reviews[0]["content_sha256"] == receipt.content_sha256
    docpath = f"/api/authored-visuals/{receipt.document_id}"
    assert (await client.get(docpath)).json()["revision"] == 2
    versions = (await client.get(docpath + "/versions")).json()
    assert [v["id"] for v in versions] == [receipt.version_id]
    assert (await client.get("/api/authored-visuals?limit=1")).json()[0][
        "id"
    ] == receipt.document_id
    assert (await client.get("/api/authored-visuals?offset=1")).json() == []
    assert (await client.get("/api/authored-visuals?limit=51")).status_code == 422
    await post(
        client,
        {
            "action": "archive",
            "document_id": receipt.document_id,
            "expected_revision": 2,
            "archived": True,
        },
        "archive",
    )
    assert (await client.get("/api/authored-visuals")).json() == []
    assert len((await client.get("/api/authored-visuals?archived=true")).json()) == 1
    assert (await client.get(path)).status_code == 200


@pytest.mark.parametrize(
    "change,expected",
    [
        ("snapshot", "snapshot_unavailable"),
        ("answer", "unavailable_or_changed"),
        ("source", "unavailable_or_changed"),
        ("trust", "source_excluded"),
        ("quarantine", "source_excluded"),
    ],
)
async def test_current_grounding_does_not_rewrite_historical_review(
    client, db, learner, change, expected
):
    receipt, path = await setup(client, db, learner, sourced=True)
    assert (await client.get(path)).json()["grounding_now"] == "sources_recorded"
    assert (await post(client, review_command(receipt), "review")).status_code == 200
    if change == "snapshot":
        await db.execute(delete(Snapshot).where(Snapshot.version_id == receipt.version_id))
    elif change == "answer":
        (await db.get(TutorAnswer, "root")).text = "Changed answer"
    elif change == "source":
        (await db.get(Chunk, "chunk")).text = "Changed source"
    else:
        provenance = await db.scalar(
            select(ChunkProvenance).where(ChunkProvenance.chunk_id == "chunk")
        )
        provenance.trust_tier = 0 if change == "trust" else 1
        if change == "quarantine":
            from app.knowledge.provenance import QUARANTINE_FLAGS

            provenance.flags_json = [next(iter(QUARANTINE_FLAGS))]
    await db.commit()
    result = (await client.get(path)).json()
    assert result["grounding_now"] == expected
    assert result["spec"] is not None
    assert (await client.get(path + "/reviews")).json()[0]["decision"] == "accept"


async def test_foreign_history_is_hidden(client, db, learner):
    receipt, path = await setup(client, db, learner)
    other = LearnerProfile(display_name="Other")
    db.add(other)
    await db.commit()

    async def other_owner():
        return other

    app = client._transport.app
    app.dependency_overrides[get_learner] = other_owner
    try:
        assert (await client.get("/api/authored-visuals")).json() == []
        for url in [
            path,
            path + "/reviews",
            f"/api/authored-visuals/{receipt.document_id}",
            f"/api/authored-visuals/{receipt.document_id}/versions",
        ]:
            assert (await client.get(url)).status_code == 404
    finally:
        del app.dependency_overrides[get_learner]


async def test_restored_invalid_spec_is_not_renderable_or_echoed(client, db, learner):
    from app.db.models import AuthoredVisualVersion as Version
    from app.kernel.authored_visuals import digest

    receipt, _ = await setup(client, db, learner)
    corrupt = '{"private-source-secret": "not a visual spec"}'
    db.add(
        Version(
            id="invalid-restored",
            learner_id=learner.id,
            document_id=receipt.document_id,
            version=2,
            spec_json=corrupt,
            content_sha256=digest(corrupt),
            binding_json="{}",
            snapshot_sha256="0" * 64,
            target_kind="answer",
            target_id="root",
        )
    )
    await db.commit()
    response = await client.get(
        f"/api/authored-visuals/{receipt.document_id}/versions/invalid-restored"
    )
    assert response.status_code == 200
    assert response.json()["spec"] is None
    assert response.json()["grounding_now"] == "invalid_content"
    assert "private-source-secret" not in response.text
