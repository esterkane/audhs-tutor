"""Area source diversity, draft safety, explicit feedback and reversible preferences."""

import pytest
from sqlalchemy import func, select

from app.db import models
from app.kernel import areas, curriculum, preferences, question_feedback, skill_graph
from app.knowledge.ingest.service import ingest_path
from app.models_ai import registry
from app.models_ai.budget import Budget
from app.models_ai.fake import FakeProvider
from app.models_ai.gateway import ModelGateway
from app.models_ai.routing import Router
from app.orchestrator import area_drafting
from app.schemas.areas import FeedbackIn

TEXT = (
    "Retrieval selects relevant passages before generation. The generator uses those passages "
    "to ground its answer. Compare the answer with source evidence because retrieved text can "
    "still be incomplete or outdated. "
)


async def sources(db, tmp_path):
    for i, course in enumerate(["Course A", "Course B"]):
        path = tmp_path / course / "Retrieval"
        path.mkdir(parents=True)
        (path / "RAG concepts.md").write_text(TEXT + f"This example uses dataset {i}.")
        await ingest_path(db, path.parent, course=course)
    await areas.seed(db)
    return (
        await db.execute(select(models.KnowledgeArea).where(models.KnowledgeArea.slug == "rag"))
    ).scalar_one()


async def test_areas_combine_courses_and_preserve_roles(db, tmp_path, learner):
    area = await sources(db, tmp_path)
    chosen, coverage = await areas.excerpts(db, area)
    assert {c["course"] for c in chosen} == {"Course A", "Course B"}
    assert coverage["selected_passages"] == 2
    cat = await areas.catalogue(db, learner.id)
    assert next(a for a in cat["areas"] if a["id"] == area.id)["courses"] == [
        "Course A",
        "Course B",
    ]
    excluded = chosen[0]
    await curriculum.set_source_role(
        db, excluded["course"], excluded["document_id"], "excluded", "not useful"
    )
    new, _ = await areas.excerpts(db, area)
    assert excluded["id"] not in {c["id"] for c in new}
    await areas.seed(db)
    assert (
        await db.execute(select(func.count()).select_from(models.KnowledgeArea))
    ).scalar() == len(areas.DEFAULTS)


def suggestion(chosen):
    return {
        "lessons": [
            {
                "title": "Grounding answers in retrieval",
                "goal": "Explain how retrieved evidence grounds an answer.",
                "exercise": "Trace which passage supports a generated factual claim.",
                "criteria": ["Distinguishes retrieving evidence from generating an answer."],
                "question": "Why does retrieving a passage not guarantee a correct generated answer?",
                "expected_answer": (
                    "The passage can be incomplete or outdated, "
                    "and the generator must still use its evidence correctly."
                ),
                "source_ids": [c["id"] for c in chosen],
                "evidence_quote": "Retrieval selects relevant passages before generation.",
            }
        ]
    }


async def test_local_draft_has_multicourse_citations_no_invented_prerequisites(
    db, tmp_path, learner, settings
):
    area = await sources(db, tmp_path)
    chosen, _ = await areas.excerpts(db, area)
    fake = FakeProvider(structured=suggestion(chosen))
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    gw = ModelGateway(db, Router(), {"ollama": fake}, Budget(0))
    did, status = await area_drafting.create_or_generate(db, settings, learner.id, area.id, gw)
    assert status == "generated"
    draft = await curriculum.get_draft(db, learner.id, did)
    assert draft.area_id == area.id and draft.course is None
    assert draft.payload_json["skills"][0]["prerequisites"] == []
    assert len(draft.payload_json["learning_objects"][0]["sources"]) == 2
    assert not [p for p in draft.validation_json if p["level"] == "error"]
    did2, status2 = await area_drafting.create_or_generate(db, settings, learner.id, area.id, gw)
    assert (did2, status2) == (did, "existing") and len(fake.calls) == 1
    await curriculum.publish_draft(db, learner.id, did)
    node = (
        await db.execute(select(models.SkillNode).where(models.SkillNode.area_id == area.id))
    ).scalar_one()
    assert node.course is None
    fresh_id, status = await area_drafting.create_or_generate(
        db, settings, learner.id, area.id, gw, force_new=True
    )
    assert fresh_id != did and status == "generated"
    assert (await curriculum.get_draft(db, learner.id, did)).status == "published"
    await preferences.set_pref(db, learner.id, "goal.area", area.id)
    assert (await skill_graph.next_skill(db, learner.id)).id == node.id


async def test_bad_evidence_and_course_metadata_never_become_questions(db, tmp_path):
    area = await sources(db, tmp_path)
    chosen, coverage = await areas.excerpts(db, area)
    s = suggestion(chosen)
    s["lessons"][0]["evidence_quote"] = "An invented quotation that is not in either passage."
    payload = area_drafting.merge(area, chosen, area_drafting.AreaSuggestion(**s), coverage)
    assert payload["assessments"] == [] and payload["area_state"] == "needs_evidence"
    s = suggestion(chosen)
    s["lessons"][0]["source_ids"] = ["invented"]
    assert not area_drafting.merge(area, chosen, area_drafting.AreaSuggestion(**s), coverage)[
        "skills"
    ]


async def test_failed_scaffold_retries_but_edited_draft_is_kept(db, tmp_path, learner, settings):
    area = await sources(db, tmp_path)
    chosen, _ = await areas.excerpts(db, area)
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    fake = FakeProvider(fail_times=2, structured=suggestion(chosen))
    gw = ModelGateway(db, Router(), {"ollama": fake}, Budget(0))
    did, status = await area_drafting.create_or_generate(db, settings, learner.id, area.id, gw)
    assert status == "generation_failed"
    fake.fail_times = 0
    did2, status = await area_drafting.create_or_generate(db, settings, learner.id, area.id, gw)
    assert did2 == did and status == "generated"


async def test_feedback_is_versioned_owned_and_does_not_touch_mastery(db, learner):
    draft = await curriculum.create_draft(
        db,
        learner.id,
        course="C",
        section=None,
        payload={
            "skills": [],
            "assessments": [
                {"kind": "explain_back", "skill": "x", "item": {"prompt": "Explain evidence."}}
            ],
        },
    )
    body = FeedbackIn(
        draft_id=draft.id,
        draft_version=1,
        question_index=0,
        verdict="bad",
        labels=["too_vague"],
        note="Use a concrete debugging example.",
    )
    first = await question_feedback.record(db, learner.id, body)
    await question_feedback.record(db, learner.id, body)
    summary = await question_feedback.summary(db, learner.id)
    assert summary["label_counts"] == {"too_vague": 1}
    assert not any(summary["preferences"].values())
    assert summary["suggestions"][0]["key"] == "questions.applied"
    assert await question_feedback.guidance(db, learner.id) == []
    assert (
        await db.execute(select(func.count()).select_from(models.CompetencyEvidence))
    ).scalar() == 0
    assert (await db.execute(select(func.count()).select_from(models.MemoryState))).scalar() == 0
    with pytest.raises(KeyError):
        await question_feedback.record(db, "another-owner", body)
    with pytest.raises(ValueError):
        await question_feedback.record(db, learner.id, body.model_copy(update={"draft_version": 2}))
    with pytest.raises(KeyError):
        await question_feedback.withdraw(db, "another-owner", first.id)
    await question_feedback.withdraw(db, learner.id, first.id)
    assert first.withdrawn_at is not None
    await question_feedback.set_guidance(db, learner.id, "questions.applied", True)
    assert "application" in " ".join(await question_feedback.guidance(db, learner.id))
    assert not (await question_feedback.summary(db, learner.id))["suggestions"]
    await question_feedback.set_guidance(db, learner.id, "questions.applied", False)
    assert await question_feedback.guidance(db, learner.id) == []
    verbs = set((await db.execute(select(models.LearningEvent.verb))).scalars())
    assert verbs == {"preferred", "undone", "adapted"}


async def test_local_area_gateway_has_no_hosted_provider(db, settings):
    settings.openai_api_key = "should-not-be-used"
    settings.anthropic_api_key = "should-not-be-used"
    gw = area_drafting.local_gateway(db, settings)
    assert set(gw.providers) == {"ollama"} and gw.budget.daily_cap_usd == 0


async def test_api_area_edit_and_feedback_validation(client):
    res = await client.post("/api/areas/initialize")
    assert res.status_code == 200
    area = res.json()["areas"][0]
    res = await client.put(
        "/api/areas/" + area["id"], json={"title": "My area", "terms": ["custom concept"]}
    )
    assert res.status_code == 200
    assert any(a["title"] == "My area" for a in res.json()["areas"])
    res = await client.post(
        "/api/areas/feedback/questions", json={"verdict": "good", "labels": ["clear"]}
    )
    assert res.status_code == 422


async def test_generated_save_cannot_overwrite_concurrent_manual_edit(db, learner, monkeypatch):
    draft = await curriculum.create_draft(
        db, learner.id, course="C", section=None, payload={"skills": [], "assessments": []}
    )
    original = curriculum.validate_payload

    async def concurrent_edit(session, payload):
        # Interleave a manual save after the generator's initial version read.
        draft.payload_json = {"skills": [], "assessments": [], "manual_note": "keep this"}
        draft.version = 2
        await session.commit()
        return await original(session, payload)

    monkeypatch.setattr(curriculum, "validate_payload", concurrent_edit)
    changed = await area_drafting.store_if_unchanged(
        db, draft.id, 1, {"skills": [], "assessments": []}, generated=True
    )
    assert not changed
    await db.refresh(draft)
    assert draft.payload_json["manual_note"] == "keep this"
    assert not await area_drafting.store_if_unchanged(
        db, draft.id, 1, {"area_state": "interrupted"}
    )


async def test_bundled_sample_data_is_not_topic_evidence(db, tmp_path, learner):
    area = await sources(db, tmp_path)
    path = tmp_path / "Billing course" / "RAG"
    path.mkdir(parents=True)
    (path / "billing.md").write_text(
        "New payment methods are verified within fifteen minutes. "
        "To add a card open your customer portal and select billing settings. "
        "You can update your contact details and view old invoices there."
    )
    await ingest_path(db, path.parent, course="Billing course")
    selected, _ = await areas.excerpts(db, area)
    assert all(x["course"] != "Billing course" for x in selected)


async def test_scaffold_start_keeps_edit_during_source_selection(
    db, tmp_path, learner, settings, monkeypatch
):
    area = await sources(db, tmp_path)
    draft = await curriculum.create_draft(
        db,
        learner.id,
        course=None,
        section=None,
        area_id=area.id,
        payload={"skills": [], "assessments": []},
        origin="area_scaffold",
    )
    original = areas.excerpts

    async def excerpts(session, row):
        result = await original(session, row)
        await curriculum.update_draft(
            session,
            learner.id,
            draft.id,
            {"skills": [], "assessments": [], "manual_note": "keep this"},
        )
        return result

    monkeypatch.setattr(areas, "excerpts", excerpts)
    _, status = await area_drafting.create_or_generate(db, settings, learner.id, area.id)
    assert status == "kept_edits"
    await db.refresh(draft)
    assert draft.payload_json["manual_note"] == "keep this"


async def test_feedback_export_and_wipe_preserves_shared_areas(db, db_path, learner, tmp_path):
    from app.db.portability import export_learner, wipe_learner
    from app.db.session import sync_connect

    await sources(db, tmp_path)
    draft = await curriculum.create_draft(
        db,
        learner.id,
        course="C",
        section=None,
        payload={
            "skills": [],
            "assessments": [{"kind": "explain_back", "item": {"prompt": "Why?"}}],
        },
    )
    await question_feedback.record(
        db,
        learner.id,
        FeedbackIn(
            draft_id=draft.id,
            draft_version=1,
            question_index=0,
            verdict="good",
            labels=["clear"],
        ),
    )
    conn = sync_connect(f"sqlite:///{db_path}")
    exported = export_learner(conn, learner.id)
    assert len(exported["question_feedback"]) == 1
    assert exported["question_feedback"][0]["snapshot_json"]
    deleted = wipe_learner(conn, learner.id)
    assert deleted["question_feedback"] == 1
    assert conn.execute("select count(*) from knowledge_area").fetchone()[0] == len(areas.DEFAULTS)
    conn.close()
