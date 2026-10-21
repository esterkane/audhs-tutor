from uuid import uuid4

import pytest

from app.core.errors import AppError
from app.db.models import CurriculumDraft, LearnerProfile
from app.knowledge import personal_memory
from app.models_ai import registry
from app.schemas.knowledge_authoring import KnowledgeMaterialInput


async def make(client, title, notes, **extra):
    response = await client.post(
        "/api/knowledge-material/drafts",
        headers={"Idempotency-Key": str(uuid4())},
        json={"title": title, "notes": notes, **extra},
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_retrieval_scopes_versions_owner_and_excludes_ai_history(client, db, fake_repo):
    old = await make(client, "Median notebook", "Median averages the two central sorted values.")
    current = await make(client, "Current investigation", "A separate current source.")
    row = await db.get(CurriculumDraft, old["id"])
    owner = row.learner_id
    # Same repository deliberately contains another learner's identical text.
    other = LearnerProfile(display_name="Another learner")
    db.add(other)
    await db.flush()
    foreign = CurriculumDraft(
        learner_id=other.id,
        title="Private other notes",
        origin="knowledge_authored",
        payload_json={"authoring": {"notes": "Median secret belongs to another learner."}},
    )
    db.add(foreign)
    await db.commit()
    indexed = set()
    await personal_memory.search(db, fake_repo, other.id, current["id"], "median", indexed)
    hits = await personal_memory.search(
        db, fake_repo, owner, current["id"], "median central", indexed
    )
    assert hits and all(m.draft_id == old["id"] for m in hits)
    before = (await client.get("/api/curriculum/drafts")).json()
    assert await personal_memory.selected(db, owner, current["id"], [hits[0].id]) == [hits[0]]
    # Only retrieval trace/index data may change, never learner drafts or history.
    assert (await client.get("/api/curriculum/drafts")).json() == before
    body = KnowledgeMaterialInput.model_validate(
        {
            k: v
            for k, v in old["payload"]["authoring"].items()
            if k in KnowledgeMaterialInput.model_fields
        }
    ).model_dump()
    changed = await client.put(
        f"/api/knowledge-material/drafts/{old['id']}",
        json={
            **body,
            "notes": "The revised notebook no longer makes that median claim.",
            "expected_version": old["version"],
        },
    )
    assert changed.status_code == 200
    with pytest.raises(AppError):
        await personal_memory.selected(db, owner, current["id"], [hits[0].id])
    revised = await personal_memory.search(db, fake_repo, owner, current["id"], "median", indexed)
    assert all(m.version == changed.json()["version"] and m.id != hits[0].id for m in revised)


async def test_selected_memory_enters_tutor_as_untrusted_context_and_is_saved_separately(
    client, db, fake_local
):
    await registry.seed_defaults(db, installed_ollama_tags={"gemma3:12b", "llama3.1:8b"})
    old = await make(
        client, "Earlier uncertainty", "I am unsure whether deployment caused the slowdown."
    )
    current = await make(
        client,
        "Evidence",
        "Timing alone does not establish cause.",
        research={
            "passage": "Timing alone does not establish cause.",
            "topic": "causation",
            "questions": [
                {
                    "id": "q1",
                    "prompt": "What is established?",
                    "findings": "Only event order.",
                    "tutor_request": "Compare my earlier uncertainty with this source.",
                }
            ],
        },
    )
    owner = (await db.get(CurriculumDraft, old["id"])).learner_id
    memory = (await personal_memory.excerpts(db, owner, current["id"]))[0]
    body = KnowledgeMaterialInput.model_validate(
        {
            k: v
            for k, v in current["payload"]["authoring"].items()
            if k in KnowledgeMaterialInput.model_fields
        }
    ).model_dump()
    body["research"]["questions"][0]["memory_ids"] = [memory.id]
    saved = (
        await client.put(
            f"/api/knowledge-material/drafts/{current['id']}", json={**body, "expected_version": 1}
        )
    ).json()
    fake_local.structured = {
        "answer_sentence": "Your earlier uncertainty remains unresolved; timing does not establish cause.",
        "source_indices": [1],
    }
    reply = await client.post(
        f"/api/knowledge-material/drafts/{current['id']}/research-tutor",
        json={"expected_version": saved["version"], "question_id": "q1", "action": "discuss"},
    )
    assert reply.status_code == 200, reply.text
    q = reply.json()["payload"]["authoring"]["research"]["questions"][0]
    assert q["findings"] == "Only event order."
    assert q["tutor_exchanges"][-1]["memories"] == [memory.model_dump()]
    assert q["tutor_exchanges"][-1]["answer"]["source_quotes"] == [
        "Timing alone does not establish cause."
    ]
    # Removing/changing an old note never rewrites this historical reply snapshot.
    history = q["tutor_exchanges"]
    dbrow = await db.get(CurriculumDraft, old["id"])
    dbrow.status = "rejected"
    await db.commit()
    blocked = await client.post(
        f"/api/knowledge-material/drafts/{current['id']}/research-tutor",
        json={
            "expected_version": reply.json()["version"],
            "question_id": "q1",
            "action": "discuss",
        },
    )
    assert blocked.status_code == 409
    persisted = await db.get(CurriculumDraft, current["id"], populate_existing=True)
    assert (
        persisted.payload_json["authoring"]["research"]["questions"][0]["tutor_exchanges"]
        == history
    )


async def test_vectors_survive_restart_and_version_only_saves_but_changed_text_is_indexed(
    client, db, fake_repo, monkeypatch
):
    from unittest.mock import AsyncMock

    old = await make(client, "Saved notebook", "Original exact evidence.")
    current = await make(client, "Current reading", "Another source.")
    owner = (await db.get(CurriculumDraft, old["id"])).learner_id
    upsert = AsyncMock(wraps=fake_repo.upsert)
    monkeypatch.setattr(fake_repo, "upsert", upsert)
    hits = await personal_memory.search(db, fake_repo, owner, current["id"], "evidence", set())
    assert upsert.await_count == 1
    # Empty process cache simulates restart; stored vectors are still authoritative.
    again = await personal_memory.search(db, fake_repo, owner, current["id"], "evidence", set())
    assert upsert.await_count == 1 and [m.id for m in again] == [m.id for m in hits]
    body = KnowledgeMaterialInput.model_validate(
        {
            k: v
            for k, v in old["payload"]["authoring"].items()
            if k in KnowledgeMaterialInput.model_fields
        }
    ).model_dump()
    versioned = (
        await client.put(
            f"/api/knowledge-material/drafts/{old['id']}",
            json={**body, "workflow_step": "write", "expected_version": 1},
        )
    ).json()
    changed_version = await personal_memory.search(
        db, fake_repo, owner, current["id"], "evidence", set()
    )
    assert upsert.await_count == 1
    assert changed_version[0].version == versioned["version"]
    assert changed_version[0].id != hits[0].id
    with pytest.raises(AppError):
        await personal_memory.selected(db, owner, current["id"], [hits[0].id])
    edited = await client.put(
        f"/api/knowledge-material/drafts/{old['id']}",
        json={
            **body,
            "notes": "Corrected exact evidence.",
            "expected_version": versioned["version"],
        },
    )
    assert edited.status_code == 200
    updated = await personal_memory.search(db, fake_repo, owner, current["id"], "evidence", set())
    assert upsert.await_count == 2 and updated[0].text == "Corrected exact evidence."
    # Missing/deleted derived vectors are repaired without trusting an in-memory manifest.
    await fake_repo.delete([personal_memory.index_id(updated[0])])
    repaired = await personal_memory.search(
        db, fake_repo, owner, current["id"], "evidence", {personal_memory.index_id(updated[0])}
    )
    assert upsert.await_count == 3 and repaired[0] == updated[0]
