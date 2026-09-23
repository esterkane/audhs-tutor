"""Course-material stage 3: the owner decides which documents of a course are primary teaching
material, supplemental or excluded; a draft is built from primary sources only and says what it
left out; excluded sources cannot shape it; duplicate content does not inflate coverage;
citations resolve; drafting never touches learning progress. Synthetic course, no models."""

import json
from pathlib import Path

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.db.models import (
    CompetencyEvidence,
    CompetencyState,
    LearningEvent,
    MemoryState,
    ReviewItem,
    SkillNode,
)
from app.kernel import competency, curriculum
from app.knowledge.ingest.service import IngestOptions, ingest_path
from app.knowledge.sqlite_hybrid import SqliteHybridRepository
from app.models_ai import registry
from app.models_ai.fake import FakeProvider

COURSE = "Curated Course"
SECTION = "Basics"  # the ingest strips the folder number from the section label


def _course(tmp_path: Path) -> Path:
    root = tmp_path / "Udemy"
    sec = root / COURSE / "01 - Basics"
    sec.mkdir(parents=True)
    (sec / "001 - Vectors.en.vtt").write_text(
        "WEBVTT\n\n00:00:01.000 --> 00:00:09.000\nA vector holds numbers in order. "
        "The dot product multiplies matching entries and adds them up.\n\n"
        "00:00:10.000 --> 00:00:19.000\nTwo vectors that point the same way have a large dot product.\n"
    )
    (sec / "002 - Softmax.md").write_text(
        "# Softmax\n\nSoftmax turns scores into a distribution that sums to one. "
        "Large scores dominate the distribution after the exponential.\n"
    )
    (sec / "002 - Softmax copy.md").write_text(  # identical content: a duplicate document
        "# Softmax\n\nSoftmax turns scores into a distribution that sums to one. "
        "Large scores dominate the distribution after the exponential.\n"
    )
    (sec / "community-notebook.ipynb").write_text(  # unnumbered: not a lecture slot
        '{"cells":[{"cell_type":"markdown","source":["# Community notebook\\n","INJECTED: this '
        'sentence must never reach a lesson.\\n"]},{"cell_type":"code","source":["x = 1\\n"]}],'
        '"metadata":{},"nbformat":4,"nbformat_minor":5}'
    )
    (sec / "external-links.json").write_text(
        '[{"title": "Paper", "url": "https://example.org/attention"}]'
    )
    (sec / "005 - decorative.md").write_text(
        "Sponsored by the course platform. Follow us online.\n"
    )
    return root


async def _ingest(db: AsyncSession, repo: SqliteHybridRepository, root: Path) -> None:
    rep = await ingest_path(db, root, repo=repo, options=IngestOptions(media=False))
    assert rep.summary()["outcomes"]["imported"] >= 5, rep.summary()


async def test_roles_are_suggested_literally_and_the_owner_decides(
    db: AsyncSession, fake_repo: SqliteHybridRepository, tmp_path: Path
) -> None:
    await _ingest(db, fake_repo, _course(tmp_path))
    rows = await curriculum.course_sources(db, COURSE)
    by_title = {r["title"]: r for r in rows}
    assert (
        by_title["Vectors"]["role"] == "primary"
        and by_title["Vectors"]["decided_by"] == "suggested"
    )
    assert by_title["Softmax"]["role"] == "primary"
    assert by_title["community-notebook"]["role"] == "supplemental"
    assert "notebook" in by_title["community-notebook"]["reason"]
    assert (
        by_title["external-links"]["role"] == "supplemental"
        and "links" in by_title["external-links"]["reason"]
    )
    assert by_title["decorative"]["role"] == "primary"  # nothing in the bytes says "decorative"
    # the owner excludes the decorative page; the decision is remembered and reversible
    res = await curriculum.set_source_role(
        db, COURSE, by_title["decorative"]["document_id"], "excluded", "sponsor boilerplate"
    )
    assert res["decided_by"] == "owner"
    rows = {r["title"]: r for r in await curriculum.course_sources(db, COURSE)}
    assert (
        rows["decorative"]["role"] == "excluded"
        and rows["decorative"]["reason"] == "sponsor boilerplate"
    )
    # documents keep their provenance and bytes: a role is a separate row, not an edit
    doc = await db.get(models.Document, by_title["decorative"]["document_id"])
    assert doc is not None and doc.course == COURSE and doc.source_type == "markdown"
    back = await curriculum.reset_source_role(db, COURSE, by_title["decorative"]["document_id"])
    assert back == {"role": "primary", "decided_by": "suggested", "reason": back["reason"]}
    # a document of another course cannot be re-roled through this course
    try:
        await curriculum.set_source_role(
            db, "Other Course", by_title["Vectors"]["document_id"], "excluded"
        )
    except KeyError:
        pass
    else:  # pragma: no cover
        raise AssertionError("cross-course role change must be refused")


async def test_draft_uses_primary_sources_only_and_says_what_it_left_out(
    db: AsyncSession,
    fake_repo: SqliteHybridRepository,
    learner: models.LearnerProfile,
    tmp_path: Path,
) -> None:
    await _ingest(db, fake_repo, _course(tmp_path))
    rows = {r["title"]: r for r in await curriculum.course_sources(db, COURSE)}
    await curriculum.set_source_role(db, COURSE, rows["decorative"]["document_id"], "excluded")

    # learning progress before: real rows (a skill with evidence, a computed state, a memory card)
    # so "unchanged" means something — drafting, editing and re-validating must not touch them
    node = SkillNode(domain="ai_ml", slug="seeded-skill", title="Seeded skill")
    db.add(node)
    await db.flush()
    db.add(
        CompetencyEvidence(learner_id=learner.id, skill_id=node.id, dimension="recall", score=0.75)
    )
    item = ReviewItem(
        learner_id=learner.id, skill_id=node.id, item_type="cloze", prompt_json={"text": "x"}
    )
    db.add(item)
    await db.flush()
    db.add(
        MemoryState(
            learner_id=learner.id,
            review_item_id=item.id,
            fsrs_card_json={},
            stability=3.5,
            difficulty=5.0,
            state="review",
            due="2030-01-01T00:00:00.000Z",
        )
    )
    await db.commit()
    await competency.refresh(db, learner.id, node.id)

    async def progress() -> tuple[int, int, int, list[tuple[str, float, int]], list[float | None]]:
        n = [
            int((await db.execute(select(func.count(t.id)))).scalar_one())
            for t in (CompetencyEvidence, MemoryState, LearningEvent)
        ]
        states = (
            await db.execute(
                select(CompetencyState.dimension, CompetencyState.score, CompetencyState.count)
                .where(CompetencyState.learner_id == learner.id)
                .order_by(CompetencyState.dimension)
            )
        ).all()
        cards = (await db.execute(select(MemoryState.stability))).scalars().all()
        return n[0], n[1], n[2], [(d, s, c) for d, s, c in states], list(cards)

    before = await progress()
    assert before[0] == 1 and before[1] == 1 and before[3] and abs(before[3][0][1] - 0.75) < 0.01
    draft = await curriculum.create_draft(db, learner.id, course=COURSE, section=SECTION)
    assert await progress() == before
    payload = draft.payload_json
    titles = [s["title"] for s in payload["skills"]]
    assert "community-notebook" not in titles and "external-links" not in titles
    assert "decorative" not in titles
    # duplicate content: two documents with the same text yield one lecture's worth of passages —
    # the copy ingested second has only duplicate chunks and therefore no lecture slot at all
    assert sum(1 for t in titles if t.startswith("Softmax")) == 1
    sources = {c for o in payload["learning_objects"] for c in o["sources"]}
    # every cited passage resolves and belongs to a primary document of this course
    for chunk_id in sources:
        p = await curriculum.passage(db, chunk_id)
        assert p is not None and p.course == COURSE
        assert p.document_title not in ("community-notebook", "external-links", "decorative")
    # the injected notebook sentence shaped nothing
    assert all("INJECTED" not in json.dumps(a) for a in payload["assessments"])
    mat = await curriculum.section_material(db, COURSE, SECTION)
    assert {d["title"] for d in mat.left_out} >= {
        "community-notebook",
        "external-links",
        "decorative",
    }
    assert sum(1 for d in mat.left_out if d["role"] == "primary") == 1  # the duplicate copy
    assert mat.unique_chunks >= len(sources)
    # coverage counts unique passages once: the Softmax text appears in two documents but is one
    # lecture with the same passages a single copy would have; the copy contributes nothing
    softmax = [lec for lec in mat.lectures if lec["title"].startswith("Softmax")]
    assert len(softmax) == 1 and len(softmax[0]["chunks"]) >= 1
    copy = next(d for d in mat.left_out if d["role"] == "primary")
    assert copy["title"].startswith("Softmax") and copy["document_id"] != softmax[0]["document_id"]
    assert mat.unique_chunks == sum(len(lec["chunks"]) for lec in mat.lectures)
    # the draft's notes say what it is built on and what it left out, with the reason
    infos = [p["message"] for p in draft.validation_json if p["level"] == "info"]
    assert any(m.startswith("built on 2 of 2 primary document(s);") for m in infos)
    # the duplicated copy is a primary document without unique passages: said, not hidden
    assert any(
        "not used (primary, suggested): 'Softmax" in m and "no unique passages" in m for m in infos
    )
    assert any("not used (excluded, owner)" in m and "decorative" in m for m in infos)
    assert any("not used (supplemental, suggested)" in m and "notebook" in m for m in infos)
    # status stays a draft; nothing is published or re-tiered
    status = {m["course"]: m for m in await curriculum.material_status(db, learner.id)}
    assert status[COURSE]["status"] == "draft" and status[COURSE]["published_skills"] == 0
    # the selection travels with the payload: an edit re-validates and keeps every note
    assert payload["selection"]["built_on"] and payload["selection"]["left_out"]
    edited = dict(payload)
    edited["skills"] = [
        dict(s, description=s.get("description", "") + " edited") for s in payload["skills"]
    ]
    version_before = draft.version
    d2 = await curriculum.update_draft(db, learner.id, draft.id, edited)
    infos2 = [p["message"] for p in d2.validation_json if p["level"] == "info"]
    assert infos2 == infos and d2.version == version_before + 1
    assert await progress() == before  # editing a draft is not learning either


async def test_all_sources_excluded_is_refused_not_an_empty_draft(
    db: AsyncSession,
    fake_repo: SqliteHybridRepository,
    learner: models.LearnerProfile,
    tmp_path: Path,
) -> None:
    await _ingest(db, fake_repo, _course(tmp_path))
    for r in await curriculum.course_sources(db, COURSE):
        await curriculum.set_source_role(db, COURSE, r["document_id"], "excluded")
    try:
        await curriculum.create_draft(db, learner.id, course=COURSE, section=SECTION)
    except ValueError as e:
        assert "no primary material" in str(e) and "Open 'Sources of" in str(e)
        assert "0 supplemental, 6 excluded" in str(e) or "excluded" in str(e)
    else:  # pragma: no cover
        raise AssertionError("a draft without primary sources must be refused")


async def test_source_routes(
    client: AsyncClient, db: AsyncSession, fake_repo: SqliteHybridRepository, tmp_path: Path
) -> None:
    await _ingest(db, fake_repo, _course(tmp_path))
    r = await client.get("/api/curriculum/sources", params={"course": COURSE})
    assert r.status_code == 200
    body = r.json()
    assert body["counts"]["supplemental"] == 2 and body["counts"]["primary"] == 4
    doc = next(s for s in body["sources"] if s["title"] == "decorative")
    r = await client.put(
        f"/api/curriculum/sources/{doc['document_id']}",
        params={"course": COURSE},
        json={"role": "excluded", "reason": "boilerplate"},
    )
    assert r.status_code == 200 and r.json()["decided_by"] == "owner"
    body = (await client.get("/api/curriculum/sources", params={"course": COURSE})).json()
    assert body["counts"]["excluded"] == 1
    r = await client.put(
        f"/api/curriculum/sources/{doc['document_id']}",
        params={"course": COURSE},
        json={"role": "sponsor"},
    )
    assert r.status_code == 422
    r = await client.put(
        "/api/curriculum/sources/nope", params={"course": COURSE}, json={"role": "excluded"}
    )
    assert r.status_code == 404
    r = await client.delete(
        f"/api/curriculum/sources/{doc['document_id']}", params={"course": COURSE}
    )
    assert r.status_code == 200 and r.json()["decided_by"] == "suggested"


async def test_an_archive_that_is_a_sections_only_material_is_primary(
    db: AsyncSession, fake_repo: SqliteHybridRepository, tmp_path: Path
) -> None:
    """A course delivered as one project bundle (the Forward-Deployed-Engineer case): its members
    are the lessons, not supplemental — unless the section also has plain lecture files."""
    import io
    import zipfile

    root = tmp_path / "Udemy"
    only = root / "Bundle Course" / "01 - Projects"
    only.mkdir(parents=True)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("projects/Project_1/README.md", "# Project 1\n\nBuild a small API.")
        z.writestr("projects/Project_2/README.md", "# Project 2\n\nAdd a queue.")
    (only / "001 - projects.zip").write_bytes(buf.getvalue())
    mixed = root / "Bundle Course" / "02 - Lectures"
    mixed.mkdir()
    (mixed / "001 - Intro.md").write_text("# Intro\n\nThe lecture itself.")
    (mixed / "002 - starter.zip").write_bytes(buf.getvalue())
    await _ingest(db, fake_repo, root)
    roles = {
        (r["section"], r["title"]): r for r in await curriculum.course_sources(db, "Bundle Course")
    }
    only_members = [r for (sec, _), r in roles.items() if sec == "Projects"]
    assert only_members and all(r["role"] == "primary" for r in only_members)
    assert all("only material" in r["reason"] for r in only_members)
    mixed_members = [r for (sec, t), r in roles.items() if sec == "Lectures" and t != "Intro"]
    assert mixed_members and all(r["role"] == "supplemental" for r in mixed_members)
    assert roles[("Lectures", "Intro")]["role"] == "primary"


async def test_model_draft_never_sees_excluded_or_supplemental_text(
    client: AsyncClient,
    db: AsyncSession,
    fake_repo: SqliteHybridRepository,
    fake_local: FakeProvider,
    tmp_path: Path,
) -> None:
    """The routed model is prompted with excerpts of *primary* documents only: the notebook's
    injected sentence and the excluded page reach neither the prompt nor the draft, and the
    model-assisted draft carries the same selection notes as the deterministic one."""
    await _ingest(db, fake_repo, _course(tmp_path))
    rows = {r["title"]: r for r in await curriculum.course_sources(db, COURSE)}
    await curriculum.set_source_role(
        db, COURSE, rows["decorative"]["document_id"], "excluded", "sponsor boilerplate"
    )
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    fake_local.structured = {"lessons": [{"slug": "basics-vectors", "goal": "Explain vectors."}]}
    r = await client.post(
        "/api/curriculum/drafts",
        json={"course": COURSE, "section": SECTION, "use_model": True},
    )
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["origin"] == "model" and d["model_call_id"]
    sent = "\n".join(m.content for call in fake_local.calls for m in call.messages)
    assert "vector holds numbers" in sent.lower() or "dot product" in sent.lower()
    assert "INJECTED" not in sent and "Sponsored" not in sent and "Follow us" not in sent
    assert "community-notebook" not in sent and "external-links" not in sent
    infos = [p["message"] for p in d["problems"] if p["level"] == "info"]
    assert any(m.startswith("built on 2 of 2 primary document(s);") for m in infos)
    assert any("not used (excluded, owner)" in m and "sponsor boilerplate" in m for m in infos)
    assert d["payload"]["selection"]["built_on"]
    # an edit over HTTP round-trips the selection and keeps the notes (they are not re-typed)
    r = await client.put(f"/api/curriculum/drafts/{d['id']}", json={"payload": d["payload"]})
    assert r.status_code == 200, r.text
    infos2 = [p["message"] for p in r.json()["problems"] if p["level"] == "info"]
    assert infos2 == infos
    # a client that drops the selection loses the notes — and the UI keeps the payload whole
    stripped = dict(d["payload"])
    stripped.pop("selection")
    r = await client.put(f"/api/curriculum/drafts/{d['id']}", json={"payload": stripped})
    assert r.status_code == 200
    assert not [p for p in r.json()["problems"] if p["level"] == "info"]
    # with everything excluded the model path is refused with the same review hint
    for row in await curriculum.course_sources(db, COURSE):
        await curriculum.set_source_role(db, COURSE, row["document_id"], "excluded")
    r = await client.post(
        "/api/curriculum/drafts",
        json={"course": COURSE, "section": SECTION, "use_model": True},
    )
    assert r.status_code == 400 and "no primary material" in r.json()["error"]["message"]


async def test_archive_members_take_one_decision(
    client: AsyncClient, db: AsyncSession, fake_repo: SqliteHybridRepository, tmp_path: Path
) -> None:
    import io
    import zipfile

    root = tmp_path / "Udemy"
    sec = root / "Zip Course" / "01 - Code"
    sec.mkdir(parents=True)
    (sec / "001 - Lecture.md").write_text("# Lecture\n\nThe lecture text about arrays.")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for i in range(3):
            z.writestr(f"code/part{i}/README.md", f"# Part {i}\n\nStarter code notes {i}.")
    (sec / "002 - starter.zip").write_bytes(buf.getvalue())
    rep = await ingest_path(db, root, repo=fake_repo, options=IngestOptions(media=False))
    assert rep.summary()["outcomes"]["imported"] == 4, rep.summary()
    r = await client.get("/api/curriculum/sources", params={"course": "Zip Course"})
    assert r.json()["counts"] == {"primary": 1, "supplemental": 3, "excluded": 0}
    r = await client.put(
        "/api/curriculum/sources-archive",
        params={"course": "Zip Course"},
        json={
            "archive": "002 - starter.zip",
            "role": "primary",
            "reason": "the code is the course",
        },
    )
    assert r.status_code == 200 and r.json() == {
        "archive": "002 - starter.zip",
        "role": "primary",
        "documents": 3,
    }
    body = (await client.get("/api/curriculum/sources", params={"course": "Zip Course"})).json()
    assert body["counts"]["primary"] == 4
    members = [s for s in body["sources"] if "!/" in s["uri"]]
    assert all(
        s["decided_by"] == "owner" and s["reason"] == "the code is the course" for s in members
    )
    r = await client.put(
        "/api/curriculum/sources-archive",
        params={"course": "Zip Course"},
        json={"archive": "missing.zip", "role": "excluded"},
    )
    assert r.status_code == 404


async def test_documents_of_one_lecture_form_one_skill(
    db: AsyncSession,
    fake_repo: SqliteHybridRepository,
    learner: models.LearnerProfile,
    tmp_path: Path,
) -> None:
    """A resources export files every asset of a lecture under `Lecture N - title/`: an archive's
    members (Dockerfile, main.py) are one lesson with all their passages — not one skill per file
    with the same title."""
    import io
    import zipfile

    root = tmp_path / "Udemy"
    sec = root / "Served Course" / "Section 1 - Serving"
    served = sec / "Lecture 0-1 - 1. Serving with FastAPI"
    served.mkdir(parents=True)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(
            "main.py", '"""The FastAPI app defines a question answering endpoint."""\napp = 1\n'
        )
        z.writestr(
            "serve.py", '"""The server installs uvicorn and exposes port 80."""\nport = 80\n'
        )
    (served / "app--6cc041d7784f.zip").write_bytes(buf.getvalue())
    other = sec / "Lecture 0-2 - 2. Tokenizers"
    other.mkdir()
    (other / "notes.md").write_text("# Tokenizers\n\nA tokenizer splits text into ids.")
    rep = await ingest_path(db, root, repo=fake_repo, options=IngestOptions(media=False))
    assert rep.summary()["outcomes"]["imported"] == 3, rep.summary()
    section = (await curriculum.sections_of(db, "Served Course"))[0]["section"]
    # next to a plain lecture file the archive is suggested supplemental; the owner makes it primary
    n = await curriculum.set_archive_role(
        db, "Served Course", "app--6cc041d7784f.zip", "primary", "the code is the lesson"
    )
    assert n == 2
    mat = await curriculum.section_material(db, "Served Course", section)
    lectures = [str(lec["lecture"]) for lec in mat.lectures]
    assert lectures == ["Serving with FastAPI", "Tokenizers"], lectures
    slot = mat.lectures[0]
    assert len(slot["documents"]) == 2 and len(slot["chunks"]) == 2
    assert {d["title"] for d in slot["documents"]} == {"main", "serve"}
    assert [c["document_id"] for c in slot["chunks"]] == [
        slot["documents"][0]["document_id"],
        slot["documents"][1]["document_id"],
    ]
    draft = await curriculum.create_draft(db, learner.id, course="Served Course", section=section)
    payload = draft.payload_json
    assert [s["title"] for s in payload["skills"]] == ["Serving with FastAPI", "Tokenizers"]
    assert ", 2 documents" in payload["skills"][0]["description"]
    obj = next(o for o in payload["learning_objects"] if o["concept"] == "Serving with FastAPI")
    assert len(obj["sources"]) == 2  # both members are cited
    built = payload["selection"]["built_on"]
    assert len(built) == 3 and sum(1 for b in built if b["lecture"] == "Serving with FastAPI") == 2
    infos = [p["message"] for p in draft.validation_json if p["level"] == "info"]
    assert any(m.startswith("built on 3 of 3 primary document(s);") for m in infos)


async def test_every_skill_gets_an_explain_back_item_with_a_rubric(
    db: AsyncSession,
    fake_repo: SqliteHybridRepository,
    learner: models.LearnerProfile,
    tmp_path: Path,
) -> None:
    """Skills require the 'explanation' dimension; a draft without an explain-back item could be
    published and never mastered. The deterministic draft adds one per skill with a literal rubric
    keyed on the lecture's vocabulary; the validator no longer warns about it."""
    await _ingest(db, fake_repo, _course(tmp_path))
    draft = await curriculum.create_draft(db, learner.id, course=COURSE, section=SECTION)
    payload = draft.payload_json
    slugs = [s["slug"] for s in payload["skills"]]
    eb = [a for a in payload["assessments"] if a["kind"] == "explain_back"]
    assert sorted(a["skill"] for a in eb) == sorted(slugs)
    for a in eb:
        assert a["item"]["prompt"].startswith("Explain '") and a["auto"] is True
        assert len(a["rubric"]) == 3 and all(r["criterion"] and r["keywords"] for r in a["rubric"])
        assert a["source_chunk_id"]
    vec = next(a for a in eb if "vectors" in a["skill"])
    assert "vector" in " ".join(vec["rubric"][0]["keywords"]) or "product" in " ".join(
        vec["rubric"][0]["keywords"]
    )
    assert not any("no explain_back item" in p["message"] for p in draft.validation_json)
    # publishing stores the rubric next to the item, and the grader rotation offers it
    rep = await curriculum.publish_draft(db, learner.id, draft.id)
    assert rep.assessments >= len(slugs)
    rows = (
        (
            await db.execute(
                select(models.Assessment).where(models.Assessment.kind == "explain_back")
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == len(slugs) and all(r.rubric_id for r in rows)
    # a criterion list turns into rubric rows with the criterion's own words as keywords
    rubric = curriculum.rubric_from_criteria(
        ["Explains why softmax outputs sum to one", "Names the exponential step"], ["fallback"]
    )
    assert rubric[0]["keywords"][:2] == ["explains", "softmax"] and rubric[1][
        "criterion"
    ].startswith("Names")


def test_path_numbers_read_both_course_layouts() -> None:
    """Section and lecture numbers come from the folder names of either export layout; a course's
    sections must never fall back to alphabetical order ("chapter 2" before "Model …") because the
    numbers were not recognised."""
    plain = "/r/Course/03 - Attention/012 - Masking.en.vtt"
    assert curriculum.path_numbers(plain) == (3, 12)
    export = "/r/Course--abc/Section 8 - Model Optimization/Lecture 7-5 - 40. Serving/app--6cc0.zip!/main.py"
    assert curriculum.path_numbers(export) == (8, 40)
    export_file = "/r/Course--abc/Section 10 - Deployment/Lecture 9-1 - 55. Intro/notes.pdf"
    assert curriculum.path_numbers(export_file) == (10, 55)
    zipped = "/r/Course/02 - Lectures/003 - starter.zip!/code/a.py"
    assert curriculum.path_numbers(zipped) == (2, 3)
    assert curriculum.path_numbers("https://x.test/a") == (None, None)
    assert curriculum.path_numbers("/r/Course/fine_tune.ipynb") == (None, None)


def test_section_label_numbers_are_a_literal_fallback() -> None:
    assert curriculum.label_number("chapter 2 Transformers Architecture") == 2
    assert curriculum.label_number("Abschnitt 7 - Deployment") == 7
    assert curriculum.label_number("Module 12: Agents") == 12
    assert curriculum.label_number("Text Classification") is None
    assert curriculum.label_number("2nd chapter") is None
    assert curriculum.label_number("chapters overview") is None
