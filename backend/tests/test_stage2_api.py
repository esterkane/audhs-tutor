from pathlib import Path

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.kernel.seed import load_seed
from app.knowledge.reindex import load_chunks
from app.knowledge.sqlite_hybrid import SqliteHybridRepository
from app.models_ai import registry
from app.models_ai.fake import FakeProvider

SEED = Path(__file__).resolve().parents[2] / "seeds" / "attention"


async def _seed(db: AsyncSession, repo: SqliteHybridRepository) -> None:
    await load_seed(db, SEED)
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    await repo.upsert(await load_chunks(db))


async def test_preferences_api(client: AsyncClient, db: AsyncSession) -> None:
    r = await client.get("/api/preferences")
    assert (
        r.status_code == 200
        and r.json()["values"]["planner.movement"] == "before"
        and len(r.json()["specs"]) >= 8
    )
    r = await client.put("/api/preferences", json={"key": "planner.movement", "value": "after"})
    assert r.status_code == 200 and r.json()["values"]["planner.movement"] == "after"
    r = await client.put("/api/preferences", json={"key": "planner.movement", "value": "nope"})
    assert r.status_code == 400
    r = await client.delete("/api/preferences/planner.movement")
    assert r.json()["values"]["planner.movement"] == "before"


async def test_plan_blocks_resume_and_map(
    client: AsyncClient,
    db: AsyncSession,
    fake_repo: SqliteHybridRepository,
    fake_local: FakeProvider,
) -> None:
    await _seed(db, fake_repo)
    preview = (await client.get("/api/plan/preview", params={"mode": "steady", "energy": 4})).json()
    assert preview["blocks"][-1]["type"] == "recap" and preview["total_min"] > 10
    s = (await client.post("/api/sessions", json={"mode": "steady", "energy": 4})).json()
    types = [b["type"] for b in s["plan"]]
    assert "new_material" in types and types[-1] == "recap"
    nm = types.index("new_material")
    r = await client.post("/api/plan/blocks/start", json={"session_id": s["id"], "index": nm})
    assert r.status_code == 200 and r.json()["allowed"]
    # early switch out of new material without a grasp check is refused (but not for save_and_stop)
    r = await client.post(
        "/api/plan/blocks/end",
        json={"session_id": s["id"], "index": nm, "switched_early": True, "reason": "switch_early"},
    )
    assert r.status_code == 200 and r.json()["allowed"] is False and "grasp" in r.json()["message"]
    r = await client.post(
        "/api/plan/blocks/end",
        json={
            "session_id": s["id"],
            "index": nm,
            "switched_early": True,
            "reason": "switch_early",
            "grasp_passed": True,
            "actual_min": 4.5,
        },
    )
    assert r.json()["allowed"] and r.json()["next_index"] == nm + 1
    verbs = [e.verb for e in (await db.execute(select(models.LearningEvent))).scalars()]
    assert "block_started" in verbs and "block_ended" in verbs

    # resume: a turn + a UI checkpoint survive a "reload"
    turn = (
        await client.post(
            "/api/tutor/turn", json={"session_id": s["id"], "text": "explain", "action": "hint"}
        )
    ).json()
    r = await client.post(
        f"/api/sessions/{s['id']}/checkpoint", json={"phase": "assess", "block_index": nm}
    )
    assert r.json()["phase"] == "assess" and r.json()["hint_level"] == 1
    cur = (await client.get("/api/sessions/current")).json()
    assert (
        cur["id"] == s["id"]
        and cur["checkpoint"]["phase"] == "assess"
        and cur["checkpoint"]["skill_id"] == turn["turn_id"]
        or cur["checkpoint"]["skill_id"]
    )
    assert cur["checkpoint"]["hint_level"] == 1

    # skill map
    m = (await client.get("/api/skills/map")).json()
    assert len(m["nodes"]) == 8 and len(m["edges"]) == 8 and m["mermaid"].startswith("graph LR")
    assert sum(1 for n in m["nodes"] if n["is_next"]) == 1

    await client.post(f"/api/sessions/{s['id']}/end", json={"energy_after": 3, "self_report": 3})
    assert (await client.get("/api/sessions/current")).json() is None


async def test_representations_keep_object_identity_and_cache(
    client: AsyncClient,
    db: AsyncSession,
    fake_repo: SqliteHybridRepository,
    fake_local: FakeProvider,
) -> None:
    await _seed(db, fake_repo)
    s = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    skill_id = s["next_skill"]["id"]
    kinds = (await client.get(f"/api/objects/{skill_id}/representations")).json()
    assert {k["kind"] for k in kinds["kinds"]} >= {"analogy", "derivation", "code"} and not any(
        k["cached"] for k in kinds["kinds"]
    )
    assert next(k for k in kinds["kinds"] if k["kind"] == "problem_first")["allowed"] is False
    fake_local.text = "(derivation) step one [1]. Next: try it."
    a = (
        await client.post(
            f"/api/objects/{skill_id}/representations/derivation", json={"session_id": s["id"]}
        )
    ).json()
    fake_local.text = "(analogy) a volume knob [1]. Next: try it."
    b = (
        await client.post(
            f"/api/objects/{skill_id}/representations/analogy", json={"session_id": s["id"]}
        )
    ).json()
    assert (
        a["object_id"] == b["object_id"]
        and a["kind"] != b["kind"]
        and not a["cached"]
        and not b["cached"]
    )
    again = (
        await client.post(
            f"/api/objects/{skill_id}/representations/derivation", json={"session_id": s["id"]}
        )
    ).json()
    assert (
        again["cached"]
        and again["representation_id"] == a["representation_id"]
        and again["content"] == a["content"]
    )
    r = await client.post(
        f"/api/objects/{skill_id}/representations/problem_first", json={"session_id": s["id"]}
    )
    assert r.status_code == 400 and "mastery" in r.json()["error"]["message"]
    r = await client.post(
        f"/api/objects/{skill_id}/representations/prefer",
        json={
            "session_id": s["id"],
            "chosen_id": b["representation_id"],
            "rejected_id": a["representation_id"],
        },
    )
    assert r.status_code == 204
    ev = [
        e
        for e in (await db.execute(select(models.LearningEvent))).scalars()
        if e.verb == "preferred"
    ]
    assert len(ev) == 1 and ev[0].context_json == {
        "representation_chosen": "analogy",
        "representation_rejected": "derivation",
    }
    calls = (await db.execute(select(models.ModelCall))).scalars().all()
    assert len(calls) == 2  # third request served from cache


async def test_challenge_round_trip(
    client: AsyncClient,
    db: AsyncSession,
    fake_repo: SqliteHybridRepository,
    fake_local: FakeProvider,
) -> None:
    await _seed(db, fake_repo)
    s = (await client.post("/api/sessions", json={"mode": "novelty", "energy": 4})).json()
    assert (await client.get("/api/challenge/modes")).json()["modes"][0]["mode"] == "planted_error"
    fake_local.structured = {
        "prompt": (
            "Scaled attention divides by d_k (not its square root) to keep the variance at one. "
            "Find the error and explain what is correct."
        ),
        "hidden_key": "It divides by sqrt(d_k), not d_k.",
        "criteria": [
            "Locates the error in the scaling factor",
            "States the correct factor sqrt(d_k)",
            "Explains the variance reason",
        ],
    }
    r = await client.post(
        "/api/challenge/start", json={"session_id": s["id"], "mode": "planted_error"}
    )
    assert r.status_code == 200, r.text
    ch = r.json()
    assert (
        ch["mode"] == "planted_error"
        and "hidden_key" not in ch
        and ch["criteria"]
        and not ch["cached"]
    )
    again = (
        await client.post(
            "/api/challenge/start", json={"session_id": s["id"], "mode": "planted_error"}
        )
    ).json()
    assert again["assessment_id"] == ch["assessment_id"] and again["cached"]
    fake_local.structured = {
        "criterion_results": [
            {"criterion": "x", "passed": True, "evidence": "sqrt"},
            {"criterion": "y", "passed": True, "evidence": "sqrt(d_k)"},
            {"criterion": "z", "passed": False, "evidence": "absent"},
        ],
        "misconception": None,
        "confidence": 0.85,
        "feedback": "You found it; the variance reason is missing.",
        "next_step": "Add why the variance grows.",
    }
    for row, criterion in zip(
        fake_local.structured["criterion_results"], ch["criteria"], strict=True
    ):
        row["criterion"] = criterion
    res = (
        await client.post(
            "/api/challenge/submit",
            json={
                "session_id": s["id"],
                "assessment_id": ch["assessment_id"],
                "answer": "the error is dividing by d_k; it should be sqrt(d_k)",
                "confidence_pre": 4,
            },
        )
    ).json()
    assert (
        res["grader_level"] == "local"
        and res["dimension"] == "application"
        and abs(res["score"] - 2 / 3) < 1e-6
    )
    assert res["review"]["due"] > s["started_at"][:10]  # delayed at least 2 days
    from datetime import UTC, datetime, timedelta

    assert datetime.fromisoformat(res["review"]["due"]) >= datetime.now(UTC) + timedelta(
        days=1, hours=23
    )
    grade_call = fake_local.calls[-1]
    assert "Reference answer (hidden from the learner)" in grade_call.messages[1].content
