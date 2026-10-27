import hashlib

from app.db.models import (
    Assessment,
    AssessmentAttempt,
    AssessmentRubric,
    Chunk,
    ChunkProvenance,
    CurriculumDraft,
    Document,
    DocumentVersion,
    LearningObject,
    Representation,
    Session,
    SkillNode,
    TutorAnswer,
)
from app.kernel import content_retirement as retire
from app.knowledge.reindex import load_chunks

HASHES = frozenset({hashlib.sha256(b"excludedplatform").hexdigest()})


async def source(db, name, uri, course):
    doc = Document(title=name, uri=uri, course=course, source_type="markdown")
    db.add(doc)
    await db.flush()
    version = DocumentVersion(document_id=doc.id, content_hash=name)
    db.add(version)
    await db.flush()
    chunk = Chunk(
        document_version_id=version.id, ordinal=0, text=name + " raw source content", token_count=8
    )
    db.add(chunk)
    await db.flush()
    db.add(
        ChunkProvenance(
            chunk_id=chunk.id, source_id=name, path=uri, source_type="markdown", course=course
        )
    )
    return doc, chunk


async def test_retirement_removes_course_content_and_reindex_payloads_but_retains_own_history(
    db, learner
):
    old, raw = await source(
        db, "excluded source", "/active/ExcludedPlatform/course/lesson.md", "Old course"
    )
    sibling, sibling_raw = await source(
        db, "same course other file", "/active/generic.md", "Old course"
    )
    kept, newraw = await source(db, "My independent notes", "/active/notes.md", None)
    skill = SkillNode(
        slug="old",
        title="Old course concept",
        description="Old explanation",
        domain="programming",
        course="Old course",
    )
    db.add(skill)
    await db.flush()
    obj = LearningObject(
        skill_id=skill.id, concept="Old concept", goal="Old goal", examples_json=["Old example"]
    )
    rubric = AssessmentRubric(criteria_json=[{"text": "Old criteria"}])
    db.add_all([obj, rubric])
    await db.flush()
    assessment = Assessment(
        skill_id=skill.id,
        kind="explain_back",
        item_json={"prompt": "Old question"},
        rubric_id=rubric.id,
    )
    representation = Representation(
        object_id=obj.id, kind="simple", content="Old cached explanation"
    )
    session = Session(learner_id=learner.id, mode="steady", energy=3)
    db.add_all([assessment, representation, session])
    await db.flush()
    attempt = AssessmentAttempt(
        learner_id=learner.id,
        assessment_id=assessment.id,
        session_id=session.id,
        answer="My own answer",
        confidence_pre=None,
        llm_result_json={},
        correct=True,
    )
    # An authored note is personal writing, even when labelled with an older course.
    own = CurriculumDraft(
        learner_id=learner.id,
        course="Old course",
        title="My writing",
        origin="knowledge_authored",
        payload_json={"authoring": {"notes": "Keep my own writing"}},
    )
    olddraft = CurriculumDraft(
        learner_id=learner.id,
        course="Old course",
        title="Old generated draft",
        origin="model",
        payload_json={"explanation": "Old material"},
    )
    answer = TutorAnswer(
        learner_id=learner.id,
        turn_id="history",
        session_id=session.id,
        surface="ask",
        request_json={},
        text="My saved discussion",
        metadata_json={},
        fingerprint="history",
    )
    db.add_all([attempt, own, olddraft, answer])
    await db.commit()
    plan = await retire.plan(db, HASHES)
    assert set(plan.documents) == {old.id, sibling.id}
    assert set(plan.chunks) == {raw.id, sibling_raw.id}
    assert own.id not in plan.drafts and olddraft.id in plan.drafts
    await retire.redact(db, plan)
    await db.commit()
    await db.refresh(raw)
    await db.refresh(representation)
    await db.refresh(own)
    await db.refresh(assessment)
    assert raw.text == "" and representation.content == ""
    assert assessment.item_json == {"content_removed": True}
    assert own.payload_json["authoring"]["notes"] == "Keep my own writing"
    assert (await db.get(AssessmentAttempt, attempt.id)).answer == "My own answer"
    assert (await db.get(TutorAnswer, answer.id)).text == "My saved discussion"
    assert await db.get(Session, session.id) is not None
    assert [chunk.id for chunk in await load_chunks(db)] == [newraw.id]
    from app.knowledge import corpus_stats
    from app.knowledge.reindex import latest_version_ids

    assert [doc.id for doc in await corpus_stats.list_documents(db)] == [kept.id]
    assert (await corpus_stats.totals(db, await latest_version_ids(db)))[:3] == (1, 1, 1)
    assert (await retire.plan(db, HASHES)).documents == []
    await retire.redact(db, plan)
    await db.commit()
    assert (await db.get(Document, kept.id)).title == "My independent notes"


def test_exclusion_matches_encoded_source_tokens_without_matching_substrings():
    assert retire.excluded("https://example.invalid/ExcludedPlatform/course", HASHES)
    assert retire.excluded("/source/%45xcludedPlatform/lesson", HASHES)
    assert not retire.excluded("/my-excludedplatformish-notes", HASHES)
