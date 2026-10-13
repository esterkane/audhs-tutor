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


async def test_answer_documents_are_distinct_paginated_and_include_manual_saves(
    client, db, learner
):
    from app.kernel.answer_visual_binding import resolve_answer_binding
    from tests.test_answer_visual_binding import saved

    spec = await ask_spec(db, learner)
    first = VisualReceipt.model_validate((await post(client, save_command(spec), "first")).json())
    second = VisualReceipt.model_validate((await post(client, save_command(spec), "second")).json())
    edited = await post(client, save_command({**spec, "title": "Edited"}, first), "edit")
    assert edited.status_code == 200
    other = await saved(db, learner, identity="other-answer")
    binding = (await resolve_answer_binding(db, learner.id, other.id)).binding
    unrelated = await post(
        client, save_command({**spec, "binding": binding.model_dump(mode="json")}), "unrelated"
    )
    assert unrelated.status_code == 200
    path = "/api/authored-visuals?answer_id=root"
    rows = (await client.get(path)).json()
    assert {row["id"] for row in rows} == {first.document_id, second.document_id}
    assert len(rows) == 2  # Multiple versions do not duplicate a document.
    pages = [(await client.get(path + f"&limit=1&offset={offset}")).json() for offset in range(3)]
    assert [page[0]["id"] for page in pages[:2]] == [row["id"] for row in rows]
    assert pages[2] == []
    assert (await client.get(path + "&limit=51")).status_code == 422
    archived = await post(
        client,
        {
            "action": "archive",
            "document_id": first.document_id,
            "expected_revision": 2,
            "archived": True,
        },
        "archive-first",
    )
    assert archived.status_code == 200
    assert [row["id"] for row in (await client.get(path)).json()] == [second.document_id]
    assert [row["id"] for row in (await client.get(path + "&archived=true")).json()] == [
        first.document_id
    ]
    restored = await post(
        client,
        {
            "action": "archive",
            "document_id": first.document_id,
            "expected_revision": 3,
            "archived": False,
        },
        "restore-first",
    )
    assert restored.status_code == 200
    assert len((await client.get(path)).json()) == 2


async def test_answer_document_filter_hides_foreign_missing_and_non_ask_targets(
    client, db, learner
):
    from tests.test_answer_visual_binding import saved

    await setup(client, db, learner)
    other = LearnerProfile(display_name="Other")
    db.add(other)
    await db.commit()
    await saved(db, other, identity="foreign-answer")
    non_ask = await saved(db, learner, identity="non-ask")
    non_ask.surface = "playground"
    await db.commit()
    responses = [
        await client.get(f"/api/authored-visuals?answer_id={identity}")
        for identity in ("foreign-answer", "missing", "non-ask")
    ]
    assert all(response.status_code == 404 for response in responses)
    assert len({response.text for response in responses}) == 1
    assert (await client.get("/api/authored-visuals?answer_id=")).status_code == 422
    assert (
        await client.get("/api/authored-visuals", params={"answer_id": "x" * 129})
    ).status_code == 422


async def test_edit_cannot_retarget_document_and_current_target_filters_legacy_history(
    client, db, learner
):
    from sqlalchemy import func

    from app.db.models import AuthoredVisualVersion as Version
    from app.kernel.answer_visual_binding import resolve_answer_binding
    from tests.test_answer_visual_binding import saved

    spec = await ask_spec(db, learner)
    receipt = VisualReceipt.model_validate(
        (await post(client, save_command(spec), "create")).json()
    )
    other = await saved(db, learner, identity="other-answer")
    binding = (await resolve_answer_binding(db, learner.id, other.id)).binding
    moved = {**spec, "binding": binding.model_dump(mode="json")}
    response = await post(client, save_command(moved, receipt), "move")
    assert response.status_code == 409
    assert (await client.get(f"/api/authored-visuals/{receipt.document_id}")).json()[
        "revision"
    ] == 1
    assert await db.scalar(select(func.count()).select_from(Version)) == 1
    # A formerly permissive client or restored archive may contain retargeted history.
    result = await post(client, save_command(spec, receipt), "edit")
    assert result.status_code == 200
    latest = await db.get(Version, result.json()["version_id"])
    db.add(
        Version(
            id="legacy-retargeted",
            learner_id=learner.id,
            document_id=receipt.document_id,
            version=3,
            spec_json=latest.spec_json,
            content_sha256=latest.content_sha256,
            binding_json=latest.binding_json,
            snapshot_sha256=latest.snapshot_sha256,
            target_kind="answer",
            target_id="other-answer",
            origin_json=latest.origin_json,
        )
    )
    await db.commit()
    assert (await client.get("/api/authored-visuals?answer_id=root")).json() == []
    assert [
        row["id"]
        for row in (await client.get("/api/authored-visuals?answer_id=other-answer")).json()
    ] == [receipt.document_id]
