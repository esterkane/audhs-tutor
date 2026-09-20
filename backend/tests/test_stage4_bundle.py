"""Stage 4 bundle: energy re-plan card, parking promote/drop, sensory preferences, models API."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.kernel import planner


def _plan(energy: int = 3) -> planner.Plan:
    return planner.plan_session(
        planner.PlanInput(
            mode="steady", energy=energy, due_reviews=4, next_skill_id="k", review_node_ids=["a"]
        )
    )


def test_replan_keeps_past_blocks_and_rescales_the_rest() -> None:
    plan = _plan(3)
    idx = plan.types().index("new_material")
    lower = planner.replan(plan, from_index=idx, energy=1)
    assert lower.blocks[:idx] == plan.blocks[:idx]
    assert lower.energy == 1 and "challenge" not in lower.types()[idx:]
    assert lower.blocks[idx].planned_min < plan.blocks[idx].planned_min
    assert lower.types()[-1] == "recap"
    planner.validate_plan(lower)
    higher = planner.replan(plan, from_index=idx, energy=5)
    assert higher.blocks[idx].planned_min > plan.blocks[idx].planned_min
    same = planner.replan(plan, from_index=idx, energy=3)
    assert [b.model_dump() for b in same.blocks] == [b.model_dump() for b in plan.blocks]


async def test_energy_checkin_raises_a_card_that_applies_to_the_session(
    client: AsyncClient, db: AsyncSession
) -> None:
    s = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    r = await client.post(
        "/api/plan/replan", json={"session_id": s["id"], "energy": 1, "from_index": 1}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["changed"] and body["proposal_id"] and body["energy"] == 1
    row = await db.get(models.Session, s["id"])
    assert row and row.energy == 1  # the learner's statement is recorded directly
    before = list(row.planned_blocks_json)
    cards = (await client.get("/api/adaptations")).json()["proposals"]
    assert cards[0]["id"] == body["proposal_id"] and cards[0]["origin"] == "planner"
    assert "Re-plan the rest of this session" in cards[0]["what"]
    dec = await client.post(
        f"/api/adaptations/{body['proposal_id']}/decide",
        json={"decision": "try", "session_id": s["id"]},
    )
    assert dec.status_code == 200
    await db.refresh(row)
    assert row.planned_blocks_json != before and row.planned_blocks_json == body["plan"]["blocks"]
    undo = await client.post(f"/api/adaptations/{body['proposal_id']}/undo")
    assert undo.status_code == 200
    await db.refresh(row)
    assert row.planned_blocks_json == before
    # the plan is back at its energy-3 lengths while the session says energy 1: a fresh card
    r2 = await client.post(
        "/api/plan/replan", json={"session_id": s["id"], "energy": 1, "from_index": 1}
    )
    assert r2.json()["changed"] is True and r2.json()["proposal_id"] != body["proposal_id"]
    # same energy as the plan → nothing to propose
    r3 = await client.post(
        "/api/plan/replan", json={"session_id": s["id"], "energy": 3, "from_index": 1}
    )
    assert r3.json()["changed"] is False and r3.json()["proposal_id"] is None


async def test_parking_promote_and_drop(client: AsyncClient) -> None:
    item = (await client.post("/api/parking", json={"text": "look up RoPE"})).json()
    promoted = await client.post(f"/api/parking/{item['id']}/promote", json={})
    assert promoted.status_code == 200
    assert (
        promoted.json()["status"] == "promoted" and promoted.json()["promoted_to"] == "next_session"
    )
    listed = (await client.get("/api/parking", params={"status": "promoted"})).json()["items"]
    assert [i["id"] for i in listed] == [item["id"]]
    bad = await client.post(f"/api/parking/{item['id']}/promote", json={"promoted_to": "no-node"})
    assert bad.status_code == 404
    dropped = await client.post(f"/api/parking/{item['id']}/drop")
    assert dropped.json()["status"] == "dropped"
    assert (await client.post("/api/parking/nope/promote", json={})).status_code == 404
    gone = await client.post(f"/api/parking/{item['id']}/promote", json={})
    assert gone.status_code == 400  # dropped items are not promotable


async def test_sensory_preferences_exist(client: AsyncClient) -> None:
    values = (await client.get("/api/preferences")).json()["values"]
    assert values["ui.theme"] == "system" and values["ui.ambient"] == "off"
    assert values["ui.font_scale"] == "normal" and values["ui.notifications"] is False
    r = await client.put("/api/preferences", json={"key": "ui.theme", "value": "dark"})
    assert r.json()["values"]["ui.theme"] == "dark"
    assert (
        await client.put("/api/preferences", json={"key": "ui.theme", "value": "neon"})
    ).status_code == 400


async def test_models_admin_api(client: AsyncClient) -> None:
    rows = (await client.get("/api/models")).json()["models"]
    ids = {r["id"] for r in rows}
    assert {"llama31-8b", "nomic-embed-text", "ms-marco-minilm-l6", "hosted-strong"} <= ids
    routing = (await client.get("/api/models/routing")).json()
    assert routing["profile"] == "default"
    chat = next(r for r in routing["routes"] if r["task"] == "chat")
    assert chat["chain"][0]["registry_id"] == "llama31-8b" and "status" in chat["chain"][0]
    added = await client.post(
        "/api/models",
        json={
            "source": "hosted",
            "repo_id": "claude-haiku-4-5",
            "tag": "claude-haiku-4-5",
            "role": "judge",
        },
    )
    assert added.status_code == 200 and added.json()["status"] == "available"  # no API key in tests
    assert (
        await client.post("/api/models", json={"source": "nope", "repo_id": "x"})
    ).status_code == 400
    # pull of a hosted model without a key fails as a job, visibly
    job = await client.post(f"/api/models/{added.json()['id']}/pull")
    assert job.status_code == 202
    import asyncio

    for _ in range(50):
        jobs = (await client.get("/api/models/jobs")).json()["jobs"]
        if jobs and jobs[0]["status"] != "running":
            break
        await asyncio.sleep(0.05)
    assert jobs[0]["status"] == "failed" and "ANTHROPIC_API_KEY" in (jobs[0]["error"] or "")
    assert (await client.post("/api/models/nope/pull")).status_code == 404
    not_ready = await client.post(f"/api/models/{added.json()['id']}/bench")
    assert not_ready.status_code == 400
    assign = await client.post("/api/models/llama31-8b/assign", json={"task": "chat"})
    assert assign.status_code == 400  # not ready / not benchmarked in the test registry


async def test_energy_round_trip_and_arm_block_lengths(
    client: AsyncClient, db: AsyncSession
) -> None:
    from app.kernel.seed import load_seed
    from tests.test_orchestrator import SEED

    await load_seed(db, SEED)
    # 3 → 1 (card declined) → 3 must return to the original minutes
    s = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
    original = [b["planned_min"] for b in s["plan"]]
    down = await client.post(
        "/api/plan/replan", json={"session_id": s["id"], "energy": 1, "from_index": 1}
    )
    assert down.json()["changed"]
    up = await client.post(
        "/api/plan/replan", json={"session_id": s["id"], "energy": 3, "from_index": 1}
    )
    assert [b["planned_min"] for b in up.json()["plan"]["blocks"]] == original
    assert (
        await client.post(
            "/api/plan/replan", json={"session_id": s["id"], "energy": 3, "from_index": 999}
        )
    ).status_code == 422
    await client.post(f"/api/sessions/{s['id']}/end", json={"energy_after": 3, "self_report": 3})
    # a session-unit arm with new_material_min actually changes the plan
    made = (
        await client.post(
            "/api/experiments/from-template", json={"template": "short-vs-long-blocks"}
        )
    ).json()
    await client.post(f"/api/experiments/{made['id']}/start")
    seen: dict[str, int] = {}
    for _ in range(4):
        s2 = (await client.post("/api/sessions", json={"mode": "steady", "energy": 3})).json()
        nm = next(b for b in s2["plan"] if b["type"] == "new_material")
        seen[s2["experiment"]["arm"]] = nm["planned_min"]
        await client.post(
            f"/api/sessions/{s2['id']}/end", json={"energy_after": 3, "self_report": 3}
        )
    assert seen == {"short": 10, "long": 25}
