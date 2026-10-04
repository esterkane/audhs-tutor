from uuid import uuid4

import httpx
from sqlalchemy import update

from app.db.models import (
    Chunk,
    Document,
    DocumentVersion,
    SessionCheckpoint,
    SkillNode,
    TutorAnswer,
)
from app.knowledge.provenance import Provenance
from app.knowledge.repository import ChunkRecord
from app.models_ai.registry import seed_defaults
from app.orchestrator.workspace_provenance import disclose


async def setup(client, db, fake_repo):
    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    session = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    db.add(
        SkillNode(
            id="source-skill",
            slug="source-skill",
            title="Vectors",
            domain="coding",
            description="Compare vectors",
            course="Synthetic",
        )
    )
    await db.execute(
        update(SessionCheckpoint)
        .where(SessionCheckpoint.session_id == session["id"])
        .values(packet_json={"skill_id": "source-skill"})
    )
    doc = Document(title="Synthetic reference", source_type="manual")
    db.add(doc)
    await db.flush()
    version = DocumentVersion(document_id=doc.id, content_hash="initial", version=1)
    db.add(version)
    await db.flush()
    records = []
    for i, text in enumerate(
        ["Vectors have components.", "Vectors can be compared by a dot product."]
    ):
        id_ = f"source-{i}"
        db.add(Chunk(id=id_, document_version_id=version.id, ordinal=i, text=text))
        records.append(
            ChunkRecord(
                id=id_,
                text=text,
                skill_ids=["source-skill"],
                provenance=Provenance(
                    source_id=doc.id,
                    path=f"reference-{i}",
                    source_type="manual",
                    course="Synthetic",
                ),
            )
        )
    await db.commit()
    await fake_repo.upsert(records)
    return {
        "session_id": session["id"],
        "lesson_origin": {"skill_id": "source-skill"},
        "learning_context": {"target_id": "lesson-test"},
        "exercise": "Client task",
        "code": "print(1)",
        "question": "Explain vectors",
        "prefer_saved": True,
    }, records


async def test_linked_sources_reuse_freshness_and_completed_replay(
    client, db, fake_repo, fake_local
):
    body, records = await setup(client, db, fake_repo)
    fake_local.text = "Vectors have components [1]."
    headers = {"Idempotency-Key": str(uuid4())}
    first = await client.post("/api/playground/tutor", json=body, headers=headers)
    assert first.status_code == 200, first.text
    result = first.json()
    assert result["source_status"] == "supplied"
    assert len(result["sources"]) == 2
    assert not result["reused"]
    prompt = fake_local.calls[-1].messages
    assert "No course sources are retrieved here" not in prompt[0].content
    assert "Vectors have components." in prompt[1].content
    assert '"goal": "Compare vectors"' in prompt[1].content
    saved = await db.get(TutorAnswer, result["answer_id"])
    assert len(saved.metadata_json["source_text_hashes"]) == 2
    calls = len(fake_local.calls)
    reused = await client.post("/api/playground/tutor", json=body)
    assert reused.json()["reused"], reused.text
    assert len(fake_local.calls) == calls
    records[0].text = "Vectors are ordered collections of components."
    await db.execute(update(Chunk).where(Chunk.id == records[0].id).values(text=records[0].text))
    await db.commit()
    await fake_repo.upsert(records)
    replay = await client.post("/api/playground/tutor", json=body, headers=headers)
    assert replay.json() == result
    assert len(fake_local.calls) == calls
    fresh = await client.post("/api/playground/tutor", json=body)
    assert fresh.status_code == 200, fresh.text
    assert not fresh.json()["reused"]
    assert len(fake_local.calls) == calls + 1


async def test_retrieval_outage_is_disclosed_without_reusing_grounded_answer(
    client, db, fake_repo, fake_local, monkeypatch
):
    body, _ = await setup(client, db, fake_repo)
    assert (await client.post("/api/playground/tutor", json=body)).status_code == 200

    async def fail(*args, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(fake_repo, "search", fail)
    response = await client.post("/api/playground/tutor", json=body)
    assert response.status_code == 200, response.text
    assert response.json()["source_status"] == "unavailable"
    assert response.json()["sources"] == []
    assert "unavailable" in response.json()["source_note"]
    assert not response.json()["reused"]


def test_source_markers_are_bounded_without_altering_code():
    assert disclose("Supported [1]", source_count=1) == ("Supported [1]", False)
    assert disclose("Unsupported [2]", source_count=1)[1]
    assert not disclose("`items[9]`", source_count=1)[1]


async def test_repository_initialization_failure_completes_disclosed_reply(
    client, db, fake_repo, monkeypatch
):
    from app.api import playground as api

    body, _ = await setup(client, db, fake_repo)

    async def unavailable(*args, **kwargs):
        raise TimeoutError("embedding probe timed out")

    monkeypatch.setattr(api, "get_repo", unavailable)
    headers = {"Idempotency-Key": str(uuid4())}
    first = await client.post("/api/playground/tutor", json=body, headers=headers)
    assert first.status_code == 200, first.text
    assert "unavailable" in first.json()["source_note"]
    replay = await client.post("/api/playground/tutor", json=body, headers=headers)
    assert replay.json() == first.json()


def test_numeric_vectors_are_not_mislabeled_as_invalid_grounded_citations():
    text = "For [1,2] and [3,4], the dot product is11 [1]."
    assert disclose(text, source_count=1) == (text, False)
    assert disclose("Unsupported source [9]", source_count=1)[1]


async def test_previous_grounded_prompt_answer_is_not_reused(client, db, fake_repo, fake_local):
    body, _ = await setup(client, db, fake_repo)
    first = await client.post("/api/playground/tutor", json=body)
    assert first.status_code == 200, first.text
    saved = await db.get(TutorAnswer, first.json()["answer_id"])
    assert saved.metadata_json["prompt_version"].endswith(".lesson.v2")
    saved.metadata_json = {
        **saved.metadata_json,
        "prompt_version": saved.metadata_json["prompt_version"].replace(".lesson.v2", ".lesson.v1"),
    }
    await db.commit()
    calls = len(fake_local.calls)
    fresh = await client.post("/api/playground/tutor", json=body)
    assert fresh.status_code == 200, fresh.text
    assert not fresh.json()["reused"]
    assert len(fake_local.calls) == calls + 1


def test_empty_grounded_lookup_does_not_mislabel_vectors_but_rejects_references():
    text = "The vectors are [1,2] and [3,4]."
    assert disclose(text, grounded=True) == (text, False)
    assert disclose("A claim [1]", grounded=True)[1]
    assert disclose(text)[1]  # Historical source-free disclosure remains conservative.
