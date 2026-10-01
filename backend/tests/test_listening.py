"""P7 guided listening: lessons from an ingested caption with a synthetic WAV next to it, bounded
clips (malformed / overlapping / over-long / beyond-audio cues skipped), text-only fallback when the
audio is missing, tasks (deterministic cloze; model MCQ with fake provider; invented answers
rejected), attempts through the ordinary grader with language-domain events, resume by progress,
answer retries, media endpoint (Range, roots), `listened` exposure event. Synthetic fixtures only."""

import shutil
import struct
import wave
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.kernel import listening, skill_graph
from app.knowledge.ingest.service import ingest_path
from app.knowledge.sqlite_hybrid import SqliteHybridRepository
from app.models_ai import registry
from app.models_ai.fake import FakeProvider

SEED = Path(__file__).resolve().parents[2] / "seeds" / "courses" / "Transformers from Scratch"
LECTURE = "01 - Inputs/001 - Tokenisation and embeddings.en.vtt"
LECTURE2 = "01 - Inputs/002 - Positional information.en.vtt"


def _silence_wav(path: Path, seconds: float) -> None:
    rate = 8000
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack("<h", 0) * int(rate * seconds))


@pytest.fixture
def course(tmp_path: Path) -> Path:
    """A copy of one seed lecture caption with a synthetic 90 s silent WAV next to it."""
    root = tmp_path / "Listening Course"
    (root / "01 - Inputs").mkdir(parents=True)
    shutil.copy(SEED / LECTURE, root / LECTURE)
    shutil.copy(SEED / LECTURE2, root / LECTURE2)
    _silence_wav(root / "01 - Inputs" / "001 - Tokenisation and embeddings.wav", 90.0)
    _silence_wav(root / "01 - Inputs" / "002 - Positional information.wav", 90.0)
    return root


async def _ingest(db: AsyncSession, repo: SqliteHybridRepository, root: Path) -> str:
    """Ingest the course; return the first lecture's document id."""
    return (await _ingest_all(db, repo, root))["Tokenisation and embeddings"]


async def _ingest_all(db: AsyncSession, repo: SqliteHybridRepository, root: Path) -> dict[str, str]:
    rep = await ingest_path(db, root, course="Listening Course", repo=repo)
    assert rep.results, rep.skipped
    docs = (
        (
            await db.execute(
                select(models.Document).where(models.Document.course == "Listening Course")
            )
        )
        .scalars()
        .all()
    )
    return {str(d.lecture): d.id for d in docs}


def test_bound_sections_skips_malformed_and_clips_overlaps() -> None:
    rows: list[tuple[str, float | None, float | None, str]] = [
        ("a", 0.0, 10.0, "first clip text"),
        ("b", None, 12.0, "no start"),
        ("c", 8.0, 20.0, "overlaps the first by two seconds"),
        ("d", 25.0, 25.0, "zero length"),
        ("e", 30.0, 29.0, "negative"),
        ("f", 40.0, 400.0, "far too long"),
        ("g", 50.0, 60.0, "   "),
        ("h", 95.0, 100.0, "beyond the audio"),
        ("i", 61.0, 62.0, "too short"),
        ("j", 70.0, 80.0, "last good clip"),
    ]
    sections, skipped = listening.bound_sections(rows, duration_s=90.0)
    assert [s.chunk_id for s in sections] == ["a", "c", "j"]
    assert (sections[1].t_start, sections[1].t_end) == (10.0, 20.0)  # clipped to the previous end
    assert [s.index for s in sections] == [0, 1, 2]
    reasons = {k["chunk_id"]: k["reason"] for k in skipped}
    assert reasons["b"] == "no timestamps" and reasons["d"] == "malformed timestamps"
    assert reasons["f"].startswith("clip longer") and reasons["h"] == "beyond the end of the audio"
    assert reasons["g"] == "too short or empty" and reasons["i"] == "too short or empty"
    # no audio → no duration check, nothing "beyond"
    sections2, skipped2 = listening.bound_sections(rows, duration_s=None)
    assert "h" in {s.chunk_id for s in sections2}


def test_media_for_finds_the_sibling_and_stays_inside_roots(tmp_path: Path, course: Path) -> None:
    vtt = course / LECTURE
    media = listening.media_for(str(vtt), [tmp_path])
    assert media is not None and media.suffix == ".wav"
    assert listening.media_for(str(vtt), [tmp_path / "elsewhere"]) is None  # outside the roots
    assert listening.media_for("", [tmp_path]) is None
    assert listening.media_for(f"{course}/x.zip!/inner.vtt", [tmp_path]) is None
    assert listening.media_duration_s(media) == pytest.approx(90.0)
    assert listening.language_of(str(vtt)) == "en"


async def test_lesson_sections_fallback_and_resume(
    client: AsyncClient,
    db: AsyncSession,
    fake_repo: SqliteHybridRepository,
    learner: models.LearnerProfile,
    course: Path,
) -> None:
    doc_id = await _ingest(db, fake_repo, course)
    r = await client.get("/api/listening/lessons")
    assert r.status_code == 200, r.text
    lesson = next(x for x in r.json()["lessons"] if x["document_id"] == doc_id)
    assert lesson["media_available"] is True and lesson["sections"] >= 1 and lesson["done"] == 0
    assert lesson["language"] == "en" and lesson["duration_s"] == pytest.approx(90.0)
    r = await client.get(f"/api/listening/lessons/{doc_id}")
    body = r.json()
    assert body["media_url"] == f"/api/listening/lessons/{doc_id}/media" and body["next_index"] == 0
    first = body["sections"][0]
    assert first["t_start"] < first["t_end"] <= 90.0 and first["text"]
    # media endpoint serves the file; a Range request gets 206
    r = await client.get(body["media_url"])
    assert r.status_code == 200 and r.headers["content-type"].startswith("audio/")
    r = await client.get(body["media_url"], headers={"Range": "bytes=0-99"})
    assert r.status_code == 206 and len(r.content) == 100
    # a task for the first clip (no ready model → deterministic cloze from the transcript)
    s = await client.post("/api/sessions", json={"mode": "steady", "energy": 3, "socratic": False})
    session_id = s.json()["id"]
    r = await client.post(
        f"/api/listening/lessons/{doc_id}/sections/0/task", json={"session_id": session_id}
    )
    assert r.status_code == 200, r.text
    task = r.json()
    assert task["origin"] == "deterministic" and task["validated"] is True
    assert task["item"]["kind"] == "cloze" and "____" in task["item"]["question"]
    assert task["citation"] and task["citation"].startswith("[Listening Course")
    assert "@00:00" in task["citation"]  # clip time in the citation
    # asking again returns the same assessment (created once)
    r2 = await client.post(
        f"/api/listening/lessons/{doc_id}/sections/0/task", json={"session_id": session_id}
    )
    assert r2.json()["item"]["id"] == task["item"]["id"]
    # playing the clip is exposure only: an event, no evidence
    r = await client.post(
        f"/api/listening/lessons/{doc_id}/sections/0/listened",
        json={"session_id": session_id, "replays": 1, "seconds": 12.5},
    )
    assert r.status_code == 204
    # answer through the ordinary grader (confidence before feedback); wrong first, retry right
    a = (await db.execute(select(models.Assessment))).scalars().first()
    assert a is not None
    answer = a.item_json["answers"][0]
    r = await client.post(
        "/api/assess/attempt",
        json={
            "session_id": session_id,
            "assessment_id": task["item"]["id"],
            "answer": "wrong",
            "confidence_pre": 2,
        },
    )
    assert r.status_code == 200 and r.json()["correct"] is False
    r = await client.post(
        "/api/assess/attempt",
        json={
            "session_id": session_id,
            "assessment_id": task["item"]["id"],
            "answer": answer,
            "confidence_pre": 4,
        },
    )
    assert r.status_code == 200 and r.json()["correct"] is True
    # evidence + FSRS scheduling on the language listening node; events in the language domain
    node = (
        await db.execute(
            select(models.SkillNode).where(models.SkillNode.slug == "lang-en-listening")
        )
    ).scalar_one()
    assert not skill_graph.teachable(node)  # never a tutor lesson
    ev = (await db.execute(select(models.CompetencyEvidence))).scalars().all()
    assert len(ev) == 2 and all(e.skill_id == node.id for e in ev)
    ms = (await db.execute(select(models.MemoryState))).scalars().all()
    assert len(ms) == 1  # one card for the clip's task, scheduled by the grader
    events = (await db.execute(select(models.LearningEvent))).scalars().all()
    by_verb = {}
    for e in events:
        by_verb.setdefault(e.verb, []).append(e)
    assert by_verb["listened"][0].domain == "language"
    assert all(e.domain == "language" for e in by_verb["attempted"])
    assert by_verb["listened"][0].result_json == {"replays": 1, "seconds": 12.5}
    # progress is derived from attempts: the lesson resumes at the next clip
    body = (await client.get(f"/api/listening/lessons/{doc_id}")).json()
    assert body["sections"][0]["done"] is True and body["sections"][0]["attempts"] == 2
    assert body["next_index"] == (1 if len(body["sections"]) > 1 else None)
    lesson = next(
        x
        for x in (await client.get("/api/listening/lessons")).json()["lessons"]
        if x["document_id"] == doc_id
    )
    assert lesson["done"] == 1
    # out-of-range clip and unknown document
    assert (
        await client.post(
            f"/api/listening/lessons/{doc_id}/sections/99/task", json={"session_id": session_id}
        )
    ).status_code == 400
    assert (await client.get("/api/listening/lessons/nope")).status_code == 404


async def test_missing_or_mismatched_audio_means_text_only(
    client: AsyncClient,
    db: AsyncSession,
    fake_repo: SqliteHybridRepository,
    learner: models.LearnerProfile,
    course: Path,
) -> None:
    wav = course / "01 - Inputs" / "001 - Tokenisation and embeddings.wav"
    wav.unlink()
    doc_id = await _ingest(db, fake_repo, course)
    body = (await client.get(f"/api/listening/lessons/{doc_id}")).json()
    assert body["media_url"] is None and "reading version" in body["media_note"]
    assert body["sections"]  # the transcript still gives clips to read
    n_text_only = len(body["sections"])
    assert (await client.get(f"/api/listening/lessons/{doc_id}/media")).status_code == 404
    # audio shorter than the transcript: every clip ends inside the audio; the rest are skipped
    _silence_wav(wav, 5.0)
    body = (await client.get(f"/api/listening/lessons/{doc_id}")).json()
    assert body["media_url"] and body["duration_s"] == pytest.approx(5.0)
    assert all(s["t_end"] <= 5.0 for s in body["sections"])
    beyond = [k for k in body["skipped"] if k["reason"] == "beyond the end of the audio"]
    assert len(body["sections"]) + len(beyond) == n_text_only


async def test_model_question_is_validated_or_replaced(
    client: AsyncClient,
    db: AsyncSession,
    fake_repo: SqliteHybridRepository,
    fake_local: FakeProvider,
    learner: models.LearnerProfile,
    course: Path,
) -> None:
    docs = await _ingest_all(db, fake_repo, course)
    doc_id, doc2 = docs["Tokenisation and embeddings"], docs["Positional information"]
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    s = await client.post("/api/sessions", json={"mode": "steady", "energy": 3, "socratic": False})
    session_id = s.json()["id"]
    lesson2 = await listening.load_lesson(db, learner.id, doc2, [course.parent])
    assert lesson2 is not None
    words = [w.strip(".,") for w in lesson2.sections[0].text.split() if len(w.strip(".,")) >= 6]
    word, word2 = words[0], words[-1]
    # an invented answer (no word from the clip) fails the deterministic check → cloze fallback
    fake_local.structured = {
        "question": "What did the lecture say about pineapples?",
        "options": ["Mango juice", "Pineapple pizza", "Coconut water", "Banana bread"],
        "answer": 1,
        "explanation": "",
    }
    r = await client.post(
        f"/api/listening/lessons/{doc_id}/sections/0/task", json={"session_id": session_id}
    )
    assert r.status_code == 200, r.text
    assert r.json()["origin"] == "deterministic" and r.json()["problems"]
    assert "shares no word" in " ".join(r.json()["problems"])
    # a grounded question is stored as a model proposal, labelled and unvalidated
    fake_local.structured = {
        "question": "According to the clip, what must text become first?",
        "options": [f"{word} things", f"{word2} instead", "sounds", "smells"],
        "answer": 0,
        "explanation": f"The clip mentions {word}.",
    }
    r = await client.post(
        f"/api/listening/lessons/{doc2}/sections/0/task", json={"session_id": session_id}
    )
    assert r.status_code == 200, r.text
    task = r.json()
    assert (
        task["origin"] == "model" and task["validated"] is False and task["item"]["kind"] == "mcq"
    )
    assert len(task["item"]["options"]) == 4
    a = await db.get(models.Assessment, task["item"]["id"])
    assert a is not None and a.item_json["listening"]["model_call_id"]
    # the model call is logged like every other
    mc = (await db.execute(select(models.ModelCall))).scalars().all()
    assert mc and mc[0].task == "gen_items"


@pytest.mark.parametrize(
    "target,index,status", [("missing", 0, 404), ("real", -1, 400), ("real", 999, 400)]
)
async def test_invalid_clip_does_not_record_exposure(
    client: AsyncClient,
    db: AsyncSession,
    fake_repo: SqliteHybridRepository,
    learner: models.LearnerProfile,
    course: Path,
    target: str,
    index: int,
    status: int,
) -> None:
    doc_id = await _ingest(db, fake_repo, course)
    session = (
        await client.post("/api/sessions", json={"mode": "steady", "energy": 3, "socratic": False})
    ).json()
    document = doc_id if target == "real" else "missing"
    response = await client.post(
        f"/api/listening/lessons/{document}/sections/{index}/listened",
        json={"session_id": session["id"], "seconds": 10},
    )
    assert response.status_code == status, response.text
    events = (
        (
            await db.execute(
                select(models.LearningEvent).where(models.LearningEvent.verb == "listened")
            )
        )
        .scalars()
        .all()
    )
    assert events == []


@pytest.mark.parametrize("action", ["task", "listened"])
async def test_listening_rejects_another_learners_session(
    client: AsyncClient,
    db: AsyncSession,
    fake_repo: SqliteHybridRepository,
    learner: models.LearnerProfile,
    course: Path,
    action: str,
) -> None:
    doc_id = await _ingest(db, fake_repo, course)
    other = models.LearnerProfile(display_name="Another test learner")
    db.add(other)
    await db.flush()
    session = models.Session(learner_id=other.id, mode="steady", energy=3)
    db.add(session)
    await db.commit()
    response = await client.post(
        f"/api/listening/lessons/{doc_id}/sections/0/{action}",
        json={"session_id": session.id, "use_model": False},
    )
    assert response.status_code == 404, response.text
    assert (await db.execute(select(models.Assessment))).scalars().all() == []
    assert (await db.execute(select(models.LearningEvent))).scalars().all() == []


async def test_mcq_round_trip_validation_and_report(
    client: AsyncClient,
    db: AsyncSession,
    fake_repo: SqliteHybridRepository,
    fake_local: FakeProvider,
    learner: models.LearnerProfile,
    course: Path,
) -> None:
    docs = await _ingest_all(db, fake_repo, course)
    doc2 = docs["Positional information"]
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    s = await client.post("/api/sessions", json={"mode": "steady", "energy": 3, "socratic": False})
    session_id = s.json()["id"]
    lesson2 = await listening.load_lesson(db, learner.id, doc2, [course.parent])
    assert lesson2 is not None
    words = [w.strip(".,") for w in lesson2.sections[0].text.split() if len(w.strip(".,")) >= 6]
    fake_local.structured = {
        "question": "What does the clip inject into the tokens?",
        "options": [f"{words[0]} order", f"{words[-1]} noise", "colour", "smell"],
        "answer": 0,
        "explanation": "The clip says so.",
    }
    task = (
        await client.post(
            f"/api/listening/lessons/{doc2}/sections/0/task", json={"session_id": session_id}
        )
    ).json()
    assert task["item"]["kind"] == "mcq" and task["validated"] is False
    # the frontend answers with the option index as a string; an unchecked item is graded at half
    # confidence and never scheduled as Easy
    r = await client.post(
        "/api/assess/attempt",
        json={
            "session_id": session_id,
            "assessment_id": task["item"]["id"],
            "answer": "0",
            "confidence_pre": 5,
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["correct"] is True and r.json()["confidence"] == 0.5
    ev = (await db.execute(select(models.CompetencyEvidence))).scalar_one()
    assert ev.weight == pytest.approx(0.5)
    log = (await db.execute(select(models.ReviewLog))).scalars().all()
    assert log and all(entry.rating <= 3 for entry in log)  # capped at Good
    # the learner checks the question → full weight from now on
    r = await client.post(
        f"/api/listening/tasks/{task['item']['id']}/validate", json={"validated": True}
    )
    assert r.status_code == 200 and r.json()["validated"] is True
    # ...and can report a wrong item, which is kept next to the assessment
    r = await client.post(
        "/api/curriculum/reports",
        json={
            "kind": "wrong_item",
            "assessment_id": task["item"]["id"],
            "note": "distractor is also true",
        },
    )
    assert r.status_code == 201 and r.json()["assessment_id"] == task["item"]["id"]
    # low capacity never waits on the model: the task for the other lecture is a cloze at once
    s2 = await client.post(
        "/api/sessions", json={"mode": "low_capacity", "energy": 1, "socratic": False}
    )
    calls_before = len((await db.execute(select(models.ModelCall))).scalars().all())
    t2 = (
        await client.post(
            f"/api/listening/lessons/{docs['Tokenisation and embeddings']}/sections/0/task",
            json={"session_id": s2.json()["id"]},
        )
    ).json()
    assert t2["origin"] == "deterministic"
    assert len((await db.execute(select(models.ModelCall))).scalars().all()) == calls_before


def test_language_and_media_guards(tmp_path: Path) -> None:
    assert listening.language_of("/x/talk.de-DE.vtt") == "de"
    assert listening.language_of("/x/talk.mlx.wav") is None  # not a language code
    assert listening.language_of("/x/talk.auto.vtt") is None
    root = tmp_path / "root"
    root.mkdir()
    (root / "lec.en.vtt").write_text("WEBVTT")
    outside = tmp_path / "outside.wav"
    outside.write_bytes(b"RIFF")
    (root / "lec.wav").symlink_to(outside)
    # a symlink pointing out of the roots is refused; a directory outside is never listed
    assert listening.media_for(str(root / "lec.en.vtt"), [root]) is None
    assert listening.media_for(str(tmp_path / "elsewhere" / "lec.en.vtt"), [root]) is None
