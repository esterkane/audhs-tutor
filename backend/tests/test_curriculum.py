"""P4 curriculum-drafts / goal-home / source-viewer: material status, deterministic draft from
ingested material, validation, publish with versioning, re-publish, reject, citation passages with a
guarded open link, content reports, goal preference narrowing next_skill."""

from pathlib import Path

from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.db.models import Assessment, Document, LearningObject, SkillNode
from app.kernel import curriculum, preferences, skill_graph
from app.knowledge.ingest.service import ingest_path
from app.knowledge.sqlite_hybrid import SqliteHybridRepository
from app.models_ai import registry
from app.models_ai.fake import FakeProvider

COURSES = Path(__file__).resolve().parents[2] / "seeds" / "courses"


async def _ingest(db: AsyncSession, repo: SqliteHybridRepository, course: str) -> None:
    report = await ingest_path(db, COURSES / course, course=course, repo=repo)
    assert report.results, report.skipped


async def test_material_status_and_deterministic_draft(
    db: AsyncSession, fake_repo: SqliteHybridRepository, learner: models.LearnerProfile
) -> None:
    await _ingest(db, fake_repo, "Transformers from Scratch")
    status = await curriculum.material_status(db, learner.id)
    row = next(m for m in status if m["course"] == "Transformers from Scratch")
    assert row["status"] == "searchable" and row["chunks"] > 0 and row["published_skills"] == 0
    sections = await curriculum.sections_of(db, "Transformers from Scratch")
    assert sections and sections[0]["documents"] >= 1
    section = sections[0]["section"]
    draft = await curriculum.create_draft(
        db, learner.id, course="Transformers from Scratch", section=section
    )
    payload = draft.payload_json
    assert draft.status == "draft" and draft.origin == "deterministic"
    assert payload["skills"] and len(payload["learning_objects"]) == len(payload["skills"])
    # prerequisites follow lecture order; every learning object links real source chunks
    slugs = [s["slug"] for s in payload["skills"]]
    for i, s in enumerate(payload["skills"]):
        assert s["prerequisites"] == ([slugs[i - 1]] if i else [])
    assert all(o["sources"] for o in payload["learning_objects"])
    # cloze candidates are cut from the source, never invented
    for a in payload["assessments"]:
        assert a["kind"] == "cloze" and a["auto"] and "____" in a["item"]["text"]
        assert a["source_chunk_id"]
    problems = [p for p in draft.validation_json]
    # the deterministic draft is honest about gaps: skills without a cloze need an assessment
    assert all(p["level"] in ("error", "warning") for p in problems)
    status = await curriculum.material_status(db, learner.id)
    assert (
        next(m for m in status if m["course"] == "Transformers from Scratch")["status"] == "draft"
    )


async def test_validation_catches_cycles_missing_pieces_and_broken_sources(
    db: AsyncSession, learner: models.LearnerProfile
) -> None:
    payload = {
        "domain": "ai_ml",
        "course": "C",
        "skills": [
            {"slug": "a", "title": "A", "prerequisites": ["b"], "success_criteria": ["x"]},
            {"slug": "b", "title": "B", "prerequisites": ["a", "ghost"], "success_criteria": []},
        ],
        "learning_objects": [{"skill": "a", "concept": "A", "goal": "g", "sources": ["nope"]}],
        "assessments": [
            {"skill": "a", "kind": "cloze", "item": {"text": "no answers"}},
            {"skill": "b", "kind": "haiku", "item": {}},
        ],
    }
    problems = await curriculum.validate_payload(db, payload)
    messages = {(p.where, p.message.split(" ")[0]) for p in problems}
    text = " | ".join(f"{p.where}: {p.message}" for p in problems)
    assert "prerequisite cycle" in text and "unknown prerequisite 'ghost'" in text
    assert "no learning object" in text and "cloze needs text and answers" in text
    assert "unsupported assessment kind" in text and "source chunk(s) no longer exist" in text
    assert ("b", "no") in messages  # no success criteria (warning)
    draft = await curriculum.create_draft(db, learner.id, course="C", section=None, payload=payload)
    try:
        await curriculum.publish_draft(db, learner.id, draft.id)
    except ValueError as e:
        assert "draft has errors" in str(e)
    else:
        raise AssertionError("publish must refuse a draft with errors")


async def test_publish_versions_objects_and_keeps_history(
    db: AsyncSession, fake_repo: SqliteHybridRepository, learner: models.LearnerProfile
) -> None:
    await _ingest(db, fake_repo, "LLM Evaluation")
    section = (await curriculum.sections_of(db, "LLM Evaluation"))[0]["section"]
    draft = await curriculum.create_draft(db, learner.id, course="LLM Evaluation", section=section)
    payload = dict(draft.payload_json)
    # the learner adds the missing assessments (one MCQ per skill without a cloze)
    have = {a["skill"] for a in payload["assessments"]}
    for s in payload["skills"]:
        if s["slug"] not in have:
            payload["assessments"].append(
                {
                    "skill": s["slug"],
                    "kind": "mcq",
                    "item": {
                        "question": f"What is {s['title']} about?",
                        "options": ["a", "b", "c", "d"],
                        "answer": 0,
                    },
                }
            )
    draft = await curriculum.update_draft(db, learner.id, draft.id, payload)
    assert draft.version == 2 and not [p for p in draft.validation_json if p["level"] == "error"]
    rep = await curriculum.publish_draft(db, learner.id, draft.id)
    assert rep.skills == len(payload["skills"]) and rep.new_object_versions == rep.skills
    assert rep.assessments >= rep.skills
    nodes = list(
        (await db.execute(select(SkillNode).where(SkillNode.course == "LLM Evaluation"))).scalars()
    )
    assert len(nodes) == rep.skills and all(skill_graph.teachable(n) for n in nodes)
    first = nodes[0]
    lo_v1 = await skill_graph.learning_object_for(db, first.id)
    assert lo_v1 is not None and lo_v1.version == 1
    # a corrected re-publish: new learning-object version, the old row stays (evidence history)
    draft2 = await curriculum.create_draft(
        db, learner.id, course="LLM Evaluation", section=section, payload=payload
    )
    payload2 = dict(draft2.payload_json)
    payload2["learning_objects"][0]["goal"] = "A corrected goal."
    await curriculum.update_draft(db, learner.id, draft2.id, payload2)
    rep2 = await curriculum.publish_draft(db, learner.id, draft2.id)
    assert (
        rep2.new_object_versions == 1 and rep2.assessments == 0
    )  # same assessments: not duplicated
    versions = list(
        (
            await db.execute(select(LearningObject).where(LearningObject.skill_id == first.id))
        ).scalars()
    )
    assert sorted(v.version for v in versions) == [1, 2]
    assert (await skill_graph.learning_object_for(db, first.id)).goal == "A corrected goal."  # type: ignore[union-attr]
    assessments = list(
        (await db.execute(select(Assessment).where(Assessment.skill_id == first.id))).scalars()
    )
    assert assessments and all(a.item_json.get("draft_id") for a in assessments)
    # a published draft cannot be edited or rejected; material status is now published
    try:
        await curriculum.update_draft(db, learner.id, draft.id, payload)
    except ValueError:
        pass
    else:
        raise AssertionError("published drafts are immutable")
    status = await curriculum.material_status(db, learner.id)
    assert next(m for m in status if m["course"] == "LLM Evaluation")["status"] == "published"
    # the goal preference narrows next_skill to the published course
    await preferences.set_pref(db, learner.id, "goal.course", "LLM Evaluation", origin="explicit")
    nxt = await skill_graph.next_skill(db, learner.id)
    assert nxt is not None and nxt.course == "LLM Evaluation"
    await preferences.set_pref(db, learner.id, "goal.course", "Nope", origin="explicit")
    assert await skill_graph.next_skill(db, learner.id) is not None  # unknown goal → whole map


async def test_reject_and_routes(
    client: AsyncClient, db: AsyncSession, fake_repo: SqliteHybridRepository
) -> None:
    await _ingest(db, fake_repo, "PyTorch Fundamentals")
    r = await client.get("/api/curriculum/material")
    assert r.status_code == 200 and any(
        c["course"] == "PyTorch Fundamentals" for c in r.json()["courses"]
    )
    secs = (
        await client.get("/api/curriculum/sections", params={"course": "PyTorch Fundamentals"})
    ).json()
    section = secs["sections"][0]["section"]
    r = await client.post(
        "/api/curriculum/drafts", json={"course": "PyTorch Fundamentals", "section": section}
    )
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["status"] == "draft" and d["payload"]["skills"]
    r = await client.post(f"/api/curriculum/drafts/{d['id']}/reject")
    assert r.json()["status"] == "rejected"
    r = await client.get("/api/curriculum/drafts")
    assert any(x["id"] == d["id"] and x["status"] == "rejected" for x in r.json()["drafts"])
    # model-assisted draft without a ready GEN_ITEMS route: the deterministic draft stands and the
    # origin says so (never "model" for a draft no model touched), with a visible note
    r = await client.post(
        "/api/curriculum/drafts",
        json={"course": "PyTorch Fundamentals", "section": section, "use_model": True},
    )
    assert r.status_code == 201, r.text
    assert r.json()["origin"] == "deterministic" and r.json()["model_call_id"] is None
    assert any("model route unavailable" in p["message"] for p in r.json()["problems"])
    # citation viewer: a chunk with neighbours and a guarded open link
    chunk_id = d["payload"]["learning_objects"][0]["sources"][0]
    r = await client.get(f"/api/curriculum/chunks/{chunk_id}")
    assert r.status_code == 200, r.text
    c = r.json()
    assert c["course"] == "PyTorch Fundamentals" and c["citation"].startswith(
        "[PyTorch Fundamentals"
    )
    # the open link is the app's guarded file endpoint (file:// is dead from an http page)
    assert c["open_url"] == f"/api/curriculum/chunks/{chunk_id}/file", c["open_url"]
    r = await client.get(c["open_url"])
    assert r.status_code == 200 and len(r.content) > 100
    r = await client.get("/api/curriculum/chunks/nope")
    assert r.status_code == 404
    # a document without a file path (or outside the roots) gets no link and no file
    await db.execute(update(Document).where(Document.uri == c["uri"]).values(uri=""))
    await db.commit()
    c2 = (await client.get(f"/api/curriculum/chunks/{chunk_id}")).json()
    assert c2["open_url"] is None
    assert (await client.get(f"/api/curriculum/chunks/{chunk_id}/file")).status_code == 404
    # malformed hand-edited JSON is refused at the boundary, not a 500
    r = await client.put(f"/api/curriculum/drafts/{d['id']}", json={"payload": {"skills": ["a"]}})
    assert r.status_code == 422
    r = await client.put(
        f"/api/curriculum/drafts/{d['id']}",
        json={"payload": {"skills": [{"slug": "a", "title": "A", "prerequisites": "b"}]}},
    )
    assert r.status_code == 422
    # content reports are kept next to the evidence and resolvable
    r = await client.post(
        "/api/curriculum/reports",
        json={
            "kind": "wrong_source",
            "chunk_id": chunk_id,
            "note": "this passage is about something else",
        },
    )
    assert r.status_code == 201 and r.json()["status"] == "open"
    rid = r.json()["id"]
    assert len((await client.get("/api/curriculum/reports")).json()["reports"]) == 1
    r = await client.post(f"/api/curriculum/reports/{rid}/resolve")
    assert r.json()["status"] == "resolved"
    assert (await client.get("/api/curriculum/reports")).json()["reports"] == []
    r = await client.post("/api/curriculum/reports", json={"kind": "nonsense"})
    assert r.status_code == 422


async def test_lecture_order_follows_file_numbers_not_labels(
    db: AsyncSession, fake_repo: SqliteHybridRepository, learner: models.LearnerProfile
) -> None:
    """Review blocker: labels are stored number-stripped, so alphabetical order inverted
    'Tokenisation → Positional information'. Order must come from the file numbers."""
    await _ingest(db, fake_repo, "Transformers from Scratch")
    sections = [s["section"] for s in await curriculum.sections_of(db, "Transformers from Scratch")]
    assert sections == ["Inputs", "Attention"]
    mat = await curriculum.section_material(db, "Transformers from Scratch", "Inputs")
    assert [lec["lecture"] for lec in mat.lectures] == [
        "Tokenisation and embeddings",
        "Positional information",
    ]
    payload = curriculum.propose_payload(mat)
    slugs = [s["slug"] for s in payload["skills"]]
    assert slugs[0].endswith("tokenisation-and-embeddings") and slugs[1].endswith(
        "positional-information"
    )
    assert payload["skills"][1]["prerequisites"] == [slugs[0]]
    # slugs are course + section scoped
    assert slugs[0].startswith("transformers-from-sc-inputs-")
    # the deterministic draft leaves criteria/examples empty (no boilerplate) and says so
    assert payload["skills"][0]["success_criteria"] == []
    assert payload["learning_objects"][0]["examples"] == []
    assert payload["skills"][0]["description"].startswith("Lecture 'Tokenisation")
    problems = await curriculum.validate_payload(db, payload)
    text = " | ".join(p.message for p in problems)
    assert "no success criteria" in text and "no exercises" in text
    # cloze blanks a content word, not the guessable title word
    for a in payload["assessments"]:
        answer = a["item"]["answers"][0].lower()
        if not a.get("guessable"):
            assert answer not in {"tokenisation", "embeddings", "positional", "information"}


def test_slugs_are_section_scoped_and_unique() -> None:
    mat1 = curriculum.SectionMaterial(
        course="C",
        section="01 Intro",
        lectures=[
            {"lecture": "Introduction", "chunks": []},
            {"lecture": "Introduction", "chunks": []},
        ],
    )
    mat2 = curriculum.SectionMaterial(
        course="C", section="02 Deep", lectures=[{"lecture": "Introduction", "chunks": []}]
    )
    s1 = curriculum.lecture_slugs(mat1)
    s2 = curriculum.lecture_slugs(mat2)
    assert len(set(s1)) == 2 and s1[1].endswith("-2")
    assert s1[0] != s2[0]  # same lecture title in two sections → two skills


def _mcq(skill: str) -> dict[str, object]:
    return {
        "skill": skill,
        "kind": "mcq",
        "item": {"question": f"{skill}?", "options": ["a", "b", "c", "d"], "answer": 0},
    }


def _payload(course: str, slug: str, prereqs: list[str]) -> dict[str, object]:
    return {
        "domain": "ai_ml",
        "course": course,
        "skills": [{"slug": slug, "title": slug.upper(), "prerequisites": prereqs}],
        "learning_objects": [{"skill": slug, "concept": slug, "goal": "g", "sources": []}],
        "assessments": [_mcq(slug)],
    }


async def test_validation_orphans_and_cycles_across_published_graph(
    db: AsyncSession, learner: models.LearnerProfile
) -> None:
    a = await curriculum.create_draft(
        db, learner.id, course="Cyc", section=None, payload=_payload("Cyc", "cyc-a", [])
    )
    await curriculum.publish_draft(db, learner.id, a.id)
    b = await curriculum.create_draft(
        db, learner.id, course="Cyc", section=None, payload=_payload("Cyc", "cyc-b", ["cyc-a"])
    )
    await curriculum.publish_draft(db, learner.id, b.id)
    # a → b is published; a new draft making a depend on b would close a cycle in the DB graph
    problems = await curriculum.validate_payload(db, _payload("Cyc", "cyc-a", ["cyc-b"]))
    assert any("prerequisite cycle" in p.message for p in problems)
    # orphan learning objects / assessments are errors (publishing would have raised KeyError)
    bad = _payload("Cyc", "cyc-c", [])
    bad["learning_objects"].append({"skill": "ghost", "concept": "x", "goal": "y"})  # type: ignore[attr-defined]
    bad["assessments"].append(_mcq("ghost"))  # type: ignore[attr-defined]
    text = " | ".join(p.message for p in await curriculum.validate_payload(db, bad))
    assert "learning object for unknown skill 'ghost'" in text
    assert "assessment for unknown skill 'ghost'" in text


async def test_goal_never_returns_a_locked_node(
    db: AsyncSession, learner: models.LearnerProfile
) -> None:
    base = await curriculum.create_draft(
        db, learner.id, course="Base", section=None, payload=_payload("Base", "base-1", [])
    )
    await curriculum.publish_draft(db, learner.id, base.id)
    goal = await curriculum.create_draft(
        db, learner.id, course="Goal", section=None, payload=_payload("Goal", "goal-1", ["base-1"])
    )
    await curriculum.publish_draft(db, learner.id, goal.id)
    await preferences.set_pref(db, learner.id, "goal.course", "Goal", origin="explicit")
    nxt = await skill_graph.next_skill(db, learner.id)
    # goal-1 is locked behind base-1: the unlocked prerequisite comes next, not the locked node
    assert nxt is not None and nxt.slug == "base-1"


async def test_model_draft_merges_proposals_and_labels_them(
    client: AsyncClient,
    db: AsyncSession,
    fake_repo: SqliteHybridRepository,
    fake_local: FakeProvider,
) -> None:
    await _ingest(db, fake_repo, "Optimization Basics")
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    section = (await curriculum.sections_of(db, "Optimization Basics"))[0]["section"]
    mat = await curriculum.section_material(db, "Optimization Basics", section)
    slug = curriculum.lecture_slugs(mat)[0]
    fake_local.structured = {
        "lessons": [
            {
                "slug": slug,
                "goal": "Explain gradient descent as a step against the gradient.",
                "exercises": ["Worked: one step by hand.", "Faded: compute the next step."],
                "mcq_question": "Which direction does gradient descent step?",
                "mcq_options": ["along", "against", "orthogonal", "random"],
                "mcq_answer": 1,
            },
            {"slug": "invented-lecture", "goal": "nope"},
        ]
    }
    r = await client.post(
        "/api/curriculum/drafts",
        json={"course": "Optimization Basics", "section": section, "use_model": True},
    )
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["origin"] == "model" and d["model_call_id"]
    obj = next(o for o in d["payload"]["learning_objects"] if o["skill"] == slug)
    assert obj["origin"] == "model" and obj["exercises"][0].startswith("Worked")
    untouched = [o for o in d["payload"]["learning_objects"] if o["skill"] != slug]
    assert all("origin" not in o for o in untouched)  # only touched lessons carry the label
    mcq = next(a for a in d["payload"]["assessments"] if a["kind"] == "mcq")
    # no fabricated provenance: the model saw several excerpts, so no single passage is claimed
    assert mcq["origin"] == "model" and mcq["source_chunk_id"] is None and mcq["auto"] is False
    assert any("model-proposed item" in p["message"] for p in d["problems"])
    assert not any(s["slug"] == "invented-lecture" for s in d["payload"]["skills"])
    # a model that keeps returning invalid output → deterministic draft, labelled as such
    fake_local.fail_structured_times = 10
    r = await client.post(
        "/api/curriculum/drafts",
        json={"course": "Optimization Basics", "section": section, "use_model": True},
    )
    assert r.status_code == 201, r.text
    assert r.json()["origin"] == "deterministic"


def test_open_target_guards(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    f = root / "lecture.vtt"
    f.write_text("WEBVTT")
    assert curriculum.open_target("", [root]) is None
    assert curriculum.open_target("https://x.test/a", [root]) is None
    assert curriculum.open_target(f"{tmp_path}/course.zip!/inner.md", [root]) is None
    assert curriculum.open_target(str(tmp_path / "outside.txt"), [root]) is None
    assert curriculum.open_target(str(root), [root]) is None  # a directory is not served
    assert curriculum.open_target(str(f), [root]) == f.resolve()
    assert curriculum.open_fragment("udemy_caption", str(f), 75.4) == "#t=75"
    assert curriculum.open_fragment("markdown", "x.md", 75.4) == ""
