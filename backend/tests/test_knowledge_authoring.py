from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models import AssessmentAttempt, CompetencyEvidence, CurriculumDraft, LearnerProfile
from app.models_ai import registry
from app.models_ai.fake import FakeProvider


async def test_local_research_questions_validate_source_and_preserve_findings(
    client: AsyncClient, db: AsyncSession, fake_local: FakeProvider
):
    await registry.seed_defaults(db, installed_ollama_tags={"gemma3:12b"})
    research = {
        "passage": material()["notes"],
        "topic": "strings",
        "questions": [{"id": "starter", "prompt": "How are strings joined?"}],
    }
    draft = (
        await client.post(
            "/api/knowledge-material/drafts",
            json=material(research=research),
            headers={"Idempotency-Key": str(uuid4())},
        )
    ).json()
    fake_local.structured = {
        "questions": [
            {
                "question": "What does + do to strings?",
                "source_quote": "Python joins strings using +.",
            },
            {"question": "What does str() produce?", "source_quote": "Convert numbers with str()."},
            {
                "question": "How would you join text to a converted number?",
                "source_quote": material()["notes"],
            },
        ]
    }
    url = f"/api/knowledge-material/drafts/{draft['id']}/research-questions"
    bad_quote = fake_local.structured["questions"][0]["source_quote"]
    fake_local.structured["questions"][0]["source_quote"] = "Invented quote"
    failed = await client.post(url, json={"expected_version": 1})
    assert failed.status_code == 422
    fake_local.structured["questions"][0]["source_quote"] = bad_quote
    result = await client.post(url, json={"expected_version": 1})
    assert result.status_code == 200, result.text
    saved = result.json()
    authored = saved["payload"]["authoring"]
    assert len(authored["research"]["questions"]) == 3
    assert authored["research_model_call_id"]
    assert authored["research"]["questions"][0]["source_quote"] == bad_quote
    assert authored["research"]["passage"] == research["passage"]
    stale = await client.post(url, json={"expected_version": 1})
    assert stale.status_code == 409
    authored["research"]["questions"][0]["findings"] = "My research"
    update = await client.put(
        f"/api/knowledge-material/drafts/{draft['id']}",
        json={**material(research=authored["research"]), "expected_version": saved["version"]},
    )
    denied = await client.post(url, json={"expected_version": update.json()["version"]})
    assert denied.status_code == 409
    assert len(fake_local.calls) == 2


async def test_research_save_resume_source_revision_and_activation(
    client: AsyncClient, db: AsyncSession
):
    research = {
        "passage": "Python joins strings using +.",
        "topic": "joining strings",
        "current": 0,
        "questions": [
            {
                "id": "q1",
                "prompt": "What types can be joined?",
                "findings": "Two strings.",
                "evidence": "Python joins strings using +.",
                "unresolved": "Other types?",
                "section": "Join strings with +.",
            }
        ],
    }
    created = await client.post(
        "/api/knowledge-material/drafts",
        json=complete(research=research),
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert created.status_code == 200, created.text
    draft = created.json()
    resumed = await client.get(f"/api/curriculum/drafts/{draft['id']}")
    from app.schemas.knowledge_authoring import KnowledgeResearch

    assert (
        resumed.json()["payload"]["authoring"]["research"]
        == KnowledgeResearch.model_validate(research).model_dump()
    )
    edited = await client.put(
        f"/api/knowledge-material/drafts/{draft['id']}",
        json={
            **complete(research=research, notes="Revised notes"),
            "expected_version": draft["version"],
        },
    )
    assert edited.status_code == 200, edited.text
    assert (
        edited.json()["payload"]["authoring"]["research"]["questions"][0]["findings"]
        == "Two strings."
    )
    stale = await client.put(
        f"/api/knowledge-material/drafts/{draft['id']}",
        json={**complete(research=research), "expected_version": draft["version"]},
    )
    assert stale.status_code == 409
    published = await client.post(
        f"/api/curriculum/drafts/{draft['id']}/publish",
        json={"expected_version": edited.json()["version"]},
    )
    assert published.status_code == 200, published.text
    assert await db.scalar(select(func.count()).select_from(CompetencyEvidence)) == 0
    assert await db.scalar(select(func.count()).select_from(AssessmentAttempt)) == 0


async def test_research_rejects_unlinked_passage_and_invalid_position(client: AsyncClient):
    research = {
        "passage": "Not in source",
        "topic": "x",
        "questions": [{"id": "q", "prompt": "Why?"}],
    }
    rejected = await client.post(
        "/api/knowledge-material/drafts",
        json=material(research=research),
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert rejected.status_code == 400, rejected.text
    research["current"] = 3
    rejected = await client.post(
        "/api/knowledge-material/drafts",
        json=material(research=research),
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert rejected.status_code == 422


def material(**changes):
    return {
        "title": "String concatenation",
        "notes": "Python joins strings using +. Convert numbers with str().",
        "domain": "programming",
        **changes,
    }


def complete(**changes):
    return material(
        objective="Combine strings and explicitly convert numbers.",
        explanation="The + operator concatenates two strings. Use str() to convert a number.",
        worked_example="'Day ' + str(3) produces 'Day 3'.",
        question="Explain why 'Room ' + 7 fails and show one valid expression producing Room 7.",
        criteria=["Distinguishes string and integer", "Uses explicit conversion"],
        **changes,
    )


async def test_notes_save_edit_replay_activate_without_learning_writes(
    client: AsyncClient, db: AsyncSession
):
    key = str(uuid4())
    created = await client.post(
        "/api/knowledge-material/drafts", json=material(), headers={"Idempotency-Key": key}
    )
    assert created.status_code == 200, created.text
    draft = created.json()
    assert draft["status"] == "draft" and draft["payload"]["skills"] == []
    replay = await client.post(
        "/api/knowledge-material/drafts", json=material(), headers={"Idempotency-Key": key}
    )
    assert replay.json()["id"] == draft["id"]
    conflict = await client.post(
        "/api/knowledge-material/drafts",
        json=material(notes="Changed"),
        headers={"Idempotency-Key": key},
    )
    assert conflict.status_code == 409
    invalid = await client.post(
        f"/api/curriculum/drafts/{draft['id']}/publish", json={"expected_version": 1}
    )
    assert invalid.status_code == 400
    edited = await client.put(
        f"/api/knowledge-material/drafts/{draft['id']}", json={**complete(), "expected_version": 1}
    )
    assert edited.status_code == 200, edited.text
    draft = edited.json()
    assert not any(p["level"] == "error" for p in draft["problems"])
    published = await client.post(
        f"/api/curriculum/drafts/{draft['id']}/publish", json={"expected_version": draft["version"]}
    )
    assert published.status_code == 200, published.text
    assert published.json()["skills"] == 1
    from app.db.models import SkillNode

    node = await db.scalar(select(SkillNode))
    reading = await client.get(f"/api/knowledge-material/skills/{node.id}/reading")
    assert reading.status_code == 200
    assert reading.json()["explanation"] == complete()["explanation"]
    assert reading.json()["worked_example"] == complete()["worked_example"]
    assert reading.json()["notes"] == material()["notes"]

    assert await db.scalar(select(func.count()).select_from(CompetencyEvidence)) == 0
    assert await db.scalar(select(func.count()).select_from(AssessmentAttempt)) == 0


async def test_upload_source_lineage_and_cross_owner_rejection(
    client: AsyncClient, db: AsyncSession, settings: Settings, tmp_path: Path
):
    settings.knowledge_authoring_root = str(tmp_path)
    uploaded = await client.post(
        "/api/knowledge-material/uploads",
        content=b"Python combines strings with +. Use str(7) for the string 7.",
        headers={"X-Filename": "..%2Fnotes.md"},
    )
    assert uploaded.status_code == 200, uploaded.text
    source = uploaded.json()
    assert source["filename"] == "notes.md" and source["text"]
    saved = await client.post(
        "/api/knowledge-material/drafts",
        json=complete(
            upload_id=source["document_id"],
            notes=source["text"],
            research={
                "passage": source["text"],
                "topic": "strings",
                "questions": [
                    {
                        "id": "upload-q",
                        "prompt": "How is a number converted?",
                        "findings": "Use str().",
                        "evidence": "Use str(7) for the string 7.",
                    }
                ],
            },
        ),
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["payload"]["learning_objects"][0]["sources"]
    assert (
        saved.json()["payload"]["authoring"]["research"]["questions"][0]["findings"] == "Use str()."
    )
    from app.kernel.knowledge_authoring import source_ids

    other = LearnerProfile(display_name="Other")
    db.add(other)
    await db.commit()
    with pytest.raises(ValueError):
        await source_ids(db, other.id, source["document_id"])
    bad = await client.post(
        "/api/knowledge-material/uploads", content=b"run this", headers={"X-Filename": "run.exe"}
    )
    assert bad.status_code == 422
    empty = await client.post(
        "/api/knowledge-material/uploads", content=b"", headers={"X-Filename": "empty.txt"}
    )
    assert empty.status_code == 422


async def test_local_proposal_keeps_notes_inactive_and_rejects_stale_versions(
    client: AsyncClient, db: AsyncSession, fake_local: FakeProvider
):
    await registry.seed_defaults(db, installed_ollama_tags={"gemma3:12b"})
    fake_local.structured = {
        k: v for k, v in complete().items() if k not in {"title", "notes", "domain"}
    }
    draft = (
        await client.post(
            "/api/knowledge-material/drafts",
            json=material(),
            headers={"Idempotency-Key": str(uuid4())},
        )
    ).json()
    proposal = await client.post(
        f"/api/knowledge-material/drafts/{draft['id']}/suggest", json={"expected_version": 1}
    )
    assert proposal.status_code == 200, proposal.text
    result = proposal.json()
    assert result["payload"]["authoring"]["notes"] == material()["notes"]
    assert result["status"] == "draft" and result["payload"]["learning_objects"]
    assert result["payload"]["authoring"]["proposal_model_call_id"]
    stale = await client.post(
        f"/api/knowledge-material/drafts/{draft['id']}/suggest", json={"expected_version": 1}
    )
    assert stale.status_code == 409
    assert len(fake_local.calls) == 1


async def test_docx_text_extraction(client: AsyncClient, settings: Settings, tmp_path: Path):
    import io
    import zipfile

    settings.knowledge_authoring_root = str(tmp_path)
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as z:
        z.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body><w:p><w:r><w:t>My uploaded example</w:t></w:r></w:p></w:body></w:document>",
        )
    response = await client.post(
        "/api/knowledge-material/uploads",
        content=data.getvalue(),
        headers={"X-Filename": "lesson.docx"},
    )
    assert response.status_code == 200, response.text
    assert "My uploaded example" in response.json()["text"]


async def test_pdf_upload_extracts_text(client: AsyncClient, settings: Settings, tmp_path: Path):
    settings.knowledge_authoring_root = str(tmp_path)
    stream = b"BT /F1 12 Tf 20 100 Td (Training median is reused for held-out data.) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    start = len(data)
    data.extend(b"xref\n0 6\n0000000000 65535 f \n")
    for offset in offsets[1:]:
        data.extend(f"{offset:010} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{start}\n%%EOF".encode())
    response = await client.post(
        "/api/knowledge-material/uploads",
        content=bytes(data),
        headers={"X-Filename": "reference.pdf"},
    )
    assert response.status_code == 200, response.text
    assert "Training median" in response.json()["text"]


async def test_generation_does_not_overwrite_a_concurrent_edit(
    client: AsyncClient, db: AsyncSession, fake_local: FakeProvider, session_factory, monkeypatch
):
    from app.kernel import curriculum
    from app.models_ai.gateway import ModelGateway

    await registry.seed_defaults(db, installed_ollama_tags={"gemma3:12b"})
    fake_local.structured = {
        k: v for k, v in complete().items() if k not in {"title", "notes", "domain"}
    }
    draft = (
        await client.post(
            "/api/knowledge-material/drafts",
            json=material(),
            headers={"Idempotency-Key": str(uuid4())},
        )
    ).json()
    original = ModelGateway.complete

    async def change_during_generation(self, *args, **kwargs):
        result = await original(self, *args, **kwargs)
        async with session_factory() as other:
            row = await other.get(CurriculumDraft, draft["id"])
            payload = {
                **row.payload_json,
                "authoring": {**row.payload_json["authoring"], "notes": "My newer notes"},
            }
            await curriculum.update_draft(
                other, row.learner_id, row.id, payload, expected_version=1
            )
        return result

    monkeypatch.setattr(ModelGateway, "complete", change_during_generation)
    result = await client.post(
        f"/api/knowledge-material/drafts/{draft['id']}/suggest", json={"expected_version": 1}
    )
    assert result.status_code == 409
    drafts = (await client.get("/api/curriculum/drafts")).json()["drafts"]
    saved = next(d for d in drafts if d["id"] == draft["id"])
    assert saved["payload"]["authoring"]["notes"] == "My newer notes"
    assert saved["payload"]["skills"] == []


async def test_active_material_revision_keeps_one_skill_and_creates_new_version(
    client: AsyncClient, db: AsyncSession
):
    from app.db.models import LearningObject, SkillNode

    draft = (
        await client.post(
            "/api/knowledge-material/drafts",
            json=complete(),
            headers={"Idempotency-Key": str(uuid4())},
        )
    ).json()
    await client.post(f"/api/curriculum/drafts/{draft['id']}/publish", json={"expected_version": 1})
    current = next(
        d
        for d in (await client.get("/api/curriculum/drafts")).json()["drafts"]
        if d["id"] == draft["id"]
    )
    key = str(uuid4())
    endpoint = f"/api/knowledge-material/drafts/{draft['id']}/revise"
    revision = await client.post(
        endpoint, json={"expected_version": current["version"]}, headers={"Idempotency-Key": key}
    )
    assert revision.status_code == 200, revision.text
    next_draft = revision.json()
    replay = await client.post(
        endpoint, json={"expected_version": current["version"]}, headers={"Idempotency-Key": key}
    )
    assert replay.json()["id"] == next_draft["id"]
    assert next_draft["payload"]["skills"][0]["slug"] == draft["payload"]["skills"][0]["slug"]
    assert await db.scalar(select(func.count()).select_from(LearningObject)) == 1
    edited = await client.put(
        f"/api/knowledge-material/drafts/{next_draft['id']}",
        json={
            **complete(),
            "notes": "My improved notes",
            "explanation": "Concatenate strings with +; explicitly convert integer values with str().",
            "expected_version": 1,
        },
    )
    assert edited.status_code == 200
    published = await client.post(
        f"/api/curriculum/drafts/{next_draft['id']}/publish",
        json={"expected_version": edited.json()["version"]},
    )
    assert published.status_code == 200, published.text
    assert await db.scalar(select(func.count()).select_from(SkillNode)) == 1
    assert await db.scalar(select(func.count()).select_from(LearningObject)) == 2
