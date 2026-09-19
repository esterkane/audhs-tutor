from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.kernel.seed import load_seed
from app.knowledge.reindex import load_chunks
from app.knowledge.sqlite_hybrid import SqliteHybridRepository
from app.models_ai import registry

SEED = Path(__file__).resolve().parents[2] / "seeds" / "attention"


@pytest.fixture
async def seeded_client(
    client: AsyncClient, db: AsyncSession, fake_repo: SqliteHybridRepository
) -> AsyncClient:
    await load_seed(db, SEED)
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b", "nomic-embed-text"})
    await fake_repo.upsert(await load_chunks(db))
    return client


def _parse_sse(body: str) -> list[tuple[str, str]]:
    out = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.split("\n") if ": " in line)
        out.append((lines["event"], lines["data"]))
    return out


async def test_full_learning_loop_over_http(seeded_client: AsyncClient, db: AsyncSession) -> None:
    c = seeded_client
    me = (await c.get("/api/learner/me")).json()
    assert me["display_name"] == "Saru"

    r = await c.post("/api/sessions", json={"mode": "steady", "energy": 3})
    assert r.status_code == 201, r.text
    s = r.json()
    assert (
        s["next_skill"]["slug"] in {"vec-dot-product", "softmax"}
        and s["review_cap"] == 10
        and s["due_reviews"] == 0
    )
    sid = s["id"]

    skills = (await c.get("/api/skills")).json()
    assert len(skills["skills"]) == 8 and skills["next_skill_id"] == s["next_skill"]["id"]
    locked = [k for k in skills["skills"] if not k["unlocked"]]
    assert len(locked) == 6

    # buffered turn
    r = await c.post(
        "/api/tutor/turn", json={"session_id": sid, "text": "Explain the dot product as similarity"}
    )
    assert r.status_code == 200, r.text
    done = r.json()
    assert done["text"].startswith("(analogy)") and done["sources"] and done["tutor_trace_id"]

    # streamed turn
    r = await c.post("/api/tutor/stream", json={"session_id": sid, "text": "hint please"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    events = _parse_sse(r.text)
    kinds = [k for k, _ in events]
    assert kinds[0] == "meta" and kinds[-1] == "done" and kinds.count("token") > 3
    assert '"action": "hint"' in events[0][1] and '"hint_level": 1' in events[0][1]

    # assessment: next item, attempt with confidence first
    skill_id = s["next_skill"]["id"]
    nxt = (await c.get("/api/assess/next", params={"session_id": sid, "skill_id": skill_id})).json()
    assert nxt["item"]["kind"] == "mcq" and "answer" not in nxt["item"] and nxt["item"]["options"]
    item = nxt["item"]
    a = await db.get(models.Assessment, item["id"])
    assert a is not None
    r = await c.post(
        "/api/assess/attempt",
        json={
            "session_id": sid,
            "assessment_id": item["id"],
            "answer": str(a.item_json["answer"]),
            "confidence_pre": 5,
            "latency_ms": 4000,
        },
    )
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["correct"] is True and res["grader_level"] == "deterministic" and res["mastery"] > 0
    assert (
        res["review"]["state"] in ("learning", "review")
        and res["calibration"] == "estimate close to result"
    )

    # review queue: nothing due now, something due in 3 days (time travel), rate it
    due_now = (await c.get("/api/review/due", params={"session_id": sid})).json()
    assert due_now["items"] == [] and due_now["cap"] == 10
    later = "2030-01-01T00:00:00+00:00"
    due_later = (await c.get("/api/review/due", params={"session_id": sid, "as_of": later})).json()
    assert (
        len(due_later["items"]) == 1
        and due_later["items"][0]["reveal"]
        and due_later["items"][0]["options"]
    )
    rid = due_later["items"][0]["item_id"]
    r = await c.post(
        f"/api/review/{rid}",
        params={"as_of": later},
        json={"session_id": sid, "rating": 3, "latency_ms": 2500},
    )
    assert (
        r.status_code == 200
        and r.json()["due"] > later
        and r.json()["predicted_retrievability"] is not None
    )

    # parking lot, end session
    r = await c.post(
        "/api/parking", json={"session_id": sid, "text": "look up RoPE later", "node_id": skill_id}
    )
    assert r.status_code == 201
    assert len((await c.get("/api/parking")).json()["items"]) == 1
    r = await c.post(f"/api/sessions/{sid}/end", json={"energy_after": 4, "self_report": 4})
    assert r.status_code == 200 and r.json()["ended_at"]

    # every turn has a trace; every attempt has evidence + FSRS
    assert len((await db.execute(select(models.TutorTrace))).scalars().all()) == 2
    assert len((await db.execute(select(models.CompetencyEvidence))).scalars().all()) == 1
    assert len((await db.execute(select(models.ReviewLog))).scalars().all()) == 2
    verbs = [e.verb for e in (await db.execute(select(models.LearningEvent))).scalars()]
    for v in (
        "started",
        "asked",
        "explained",
        "attempted",
        "graded",
        "evidenced",
        "reviewed",
        "parked",
        "ended",
    ):
        assert v in verbs, v

    # errors are shaped
    r = await c.post("/api/tutor/turn", json={"session_id": sid, "text": "x"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_request"
    r = await c.get("/api/sessions/nope")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"


async def test_stream_reports_errors_as_events(seeded_client: AsyncClient) -> None:
    r = await seeded_client.post("/api/tutor/stream", json={"session_id": "missing", "text": "hi"})
    assert r.status_code == 200
    events = _parse_sse(r.text)
    assert events[-1][0] == "error" and "not found" in events[-1][1]
