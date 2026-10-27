import pytest
from sqlalchemy import select

from app.db.models import Document, LearnerPreference, SkillNode
from app.kernel import content_access, skill_graph
from app.kernel.learning_scope import REFERENCE_BEFORE
from app.knowledge.provenance import Provenance
from app.knowledge.repository import ChunkRecord, SearchFilters
from app.knowledge.study_scope import StudyRepository


async def boundary(db, learner):
    db.add(
        LearnerPreference(
            learner_id=learner.id,
            key=REFERENCE_BEFORE,
            value_json="2026-10-26T12:00:00+00:00",
            origin="explicit",
        )
    )
    await db.commit()


async def test_reset_hides_old_map_nodes_without_deleting_history_rows(db, learner):
    old = SkillNode(
        slug="old",
        title="Old material",
        domain="programming",
        created_at="2026-10-25T12:00:00+00:00",
    )
    new = SkillNode(
        slug="new",
        title="New material",
        domain="programming",
        created_at="2026-10-27T12:00:00+00:00",
    )
    db.add_all([old, new])
    await db.commit()
    await boundary(db, learner)
    nodes = await skill_graph.all_nodes(db, learner_id=learner.id)
    assert [n.id for n in nodes] == [new.id]
    assert await db.get(SkillNode, old.id) is not None
    with pytest.raises(KeyError):
        await skill_graph.get_node(db, old.id, learner_id=learner.id)
    assert (await content_access.require_skill(db, learner.id, new.id)).id == new.id


async def test_old_corpus_is_not_retrieved_for_ordinary_study(db, learner, fake_repo):
    old = Document(
        title="Accuracy reference", source_type="manual", created_at="2026-10-25T12:00:00+00:00"
    )
    new = Document(
        title="New uploaded source", source_type="manual", created_at="2026-10-27T12:00:00+00:00"
    )
    db.add_all([old, new])
    await db.commit()
    await fake_repo.upsert(
        [
            ChunkRecord(
                id=name,
                text="PostgreSQL source",
                document_id=doc.id,
                provenance=Provenance(source_id=name, path="synthetic", source_type="manual"),
            )
            for name, doc in [("old", old), ("new", new)]
        ]
    )
    await boundary(db, learner)
    scoped = StudyRepository(fake_repo, db, learner.id)
    assert [h.chunk.id for h in (await scoped.search("PostgreSQL")).hits] == ["new"]
    assert not (await scoped.search("PostgreSQL", SearchFilters(document_ids=[old.id]))).hits
    assert {h.chunk.id for h in (await fake_repo.search("PostgreSQL")).hits} == {"old", "new"}
    assert len(list(await db.scalars(select(Document)))) == 2


async def test_accuracy_review_endpoint_is_explicit_and_cannot_enable_study_sources(
    client, db, learner, fake_repo
):
    old = Document(
        title="Historical accuracy reference",
        source_type="manual",
        created_at="2026-10-25T12:00:00+00:00",
    )
    db.add(old)
    await db.commit()
    await fake_repo.upsert(
        [
            ChunkRecord(
                id="reference",
                text="PostgreSQL historical reference",
                document_id=old.id,
                provenance=Provenance(
                    source_id="reference", path="synthetic", source_type="manual"
                ),
            )
        ]
    )
    await boundary(db, learner)
    from app.api.deps import get_learner

    async def owner():
        return learner

    client._transport.app.dependency_overrides[get_learner] = owner
    # get_repo independently resolves the same first learner in this isolated database.
    regular = await client.post("/api/corpus/search", json={"query": "PostgreSQL"})
    assert regular.status_code == 200, regular.text
    assert regular.json()["hits"] == []
    review = await client.post("/api/corpus/accuracy-review/search", json={"query": "PostgreSQL"})
    assert review.status_code == 200, review.text
    assert review.json()["purpose"] == "accuracy_review"
    assert review.json()["eligible_for_course_building"] is False
    assert [h["chunk_id"] for h in review.json()["hits"]] == ["reference"]
    again = await client.post("/api/corpus/search", json={"query": "PostgreSQL"})
    assert again.json()["hits"] == []


async def test_historical_answer_cannot_become_new_lesson(db, learner):
    from app.core.errors import AppError
    from app.db.models import TutorAnswer
    from app.kernel.answer_lesson_binding import resolve_lesson_binding

    answer = TutorAnswer(
        id="old-answer",
        learner_id=learner.id,
        turn_id="old-turn",
        session_id=None,
        surface="ask",
        request_json={"question": "Old question"},
        text="Old explanation",
        metadata_json={},
        fingerprint="test",
        created_at="2026-10-25T12:00:00+00:00",
    )
    db.add(answer)
    await db.commit()
    await boundary(db, learner)
    with pytest.raises(AppError) as error:
        await resolve_lesson_binding(db, learner.id, answer.id)
    assert error.value.code == "accuracy_review_only"
    assert await db.get(TutorAnswer, answer.id) is not None


async def test_old_upload_cannot_seed_new_material_but_explicit_reupload_can(
    client, db, learner, settings, tmp_path
):
    from uuid import uuid4

    from app.kernel.focus_reset import apply

    settings.knowledge_authoring_root = str(tmp_path)
    raw = b"Synthetic source notes about separate database checks."
    before = await client.post(
        "/api/knowledge-material/uploads", content=raw, headers={"X-Filename": "source.md"}
    )
    assert before.status_code == 200, before.text
    old = before.json()["document_id"]
    await apply(db, learner.id)
    value = {
        "title": "My new database notes",
        "notes": raw.decode(),
        "focus_topic": "supabase",
        "upload_id": old,
    }
    denied = await client.post(
        "/api/knowledge-material/drafts", json=value, headers={"Idempotency-Key": str(uuid4())}
    )
    assert denied.status_code == 409 and denied.json()["error"]["code"] == "accuracy_review_only"
    again = await client.post(
        "/api/knowledge-material/uploads", content=raw, headers={"X-Filename": "source.md"}
    )
    assert again.status_code == 200, again.text
    assert again.json()["document_id"] != old
    allowed = await client.post(
        "/api/knowledge-material/drafts",
        json={**value, "upload_id": again.json()["document_id"]},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert allowed.status_code == 200, allowed.text
    assert (await db.get(Document, old)) is not None


async def test_old_draft_cannot_call_authoring_models_or_legacy_course_builder(client, db, learner):
    from sqlalchemy import func

    from app.db.models import CurriculumDraft, ModelCall

    old = CurriculumDraft(
        learner_id=learner.id,
        title="Historical draft",
        created_at="2026-10-25T12:00:00+00:00",
        payload_json={},
    )
    db.add(old)
    await db.commit()
    await boundary(db, learner)
    for suffix, body in [
        ("research-questions", {"expected_version": 1}),
        ("suggest", {"expected_version": 1}),
        ("research-tutor", {"expected_version": 1, "question_id": "q", "action": "discuss"}),
    ]:
        response = await client.post(f"/api/knowledge-material/drafts/{old.id}/{suffix}", json=body)
        assert response.status_code == 409, response.text
    response = await client.post("/api/areas/draft-job/start", json={})
    assert response.status_code == 409, response.text
    assert await db.scalar(select(func.count()).select_from(ModelCall)) == 0
