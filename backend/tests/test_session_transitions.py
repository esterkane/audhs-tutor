"""P1 session-transitions / soft-timer-identity / curriculum-eligibility: the server owns the
block state; every transition is idempotent; exactly one block_started / block_ended per block;
movement and domain blocks are `practice`; the active skill is persisted; a running block is
closed by session end; vocabulary decks are never the next teaching skill."""

from pathlib import Path

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.db.models import LearningEvent, SkillNode
from app.kernel import blocks, practice, skill_graph
from app.kernel import session as ksession
from app.kernel.seed import load_seed
from app.knowledge.reindex import load_chunks
from app.knowledge.sqlite_hybrid import SqliteHybridRepository
from app.models_ai import registry

SEED = Path(__file__).resolve().parents[2] / "seeds" / "attention"


async def _seed(db: AsyncSession, repo: SqliteHybridRepository) -> None:
    await load_seed(db, SEED)
    await registry.seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    await repo.upsert(await load_chunks(db))


async def _events(db: AsyncSession, session_id: str, verb: str) -> list[LearningEvent]:
    rows = (
        await db.execute(
            select(LearningEvent)
            .where(LearningEvent.session_id == session_id, LearningEvent.verb == verb)
            .order_by(LearningEvent.ts)
        )
    ).scalars()
    return list(rows)


async def _start(client: AsyncClient, *, mode: str = "steady", energy: int = 4) -> dict:  # type: ignore[type-arg]
    await client.put("/api/preferences", json={"key": "planner.guitar", "value": True})
    r = await client.post("/api/sessions", json={"mode": mode, "energy": energy})
    assert r.status_code == 201, r.text
    return dict(r.json())


async def test_full_journey_with_reload_at_every_boundary(
    client: AsyncClient, db: AsyncSession, fake_repo: SqliteHybridRepository
) -> None:
    await _seed(db, fake_repo)
    s = await _start(client)
    types = [b["type"] for b in s["plan"]]
    assert types[0] == "movement_primer" and "domain_switch" in types and types[-1] == "recap"
    st = s["state"]
    assert st["block_index"] is None and st["skill_id"] == s["next_skill"]["id"]  # active skill
    sid = s["id"]

    # the learner starts the plan (Home): block 0 = movement → practice screen
    r = await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 0})
    st = r.json()
    assert st["allowed"] and st["block_index"] == 0 and st["phase"] == "practice"
    assert (
        st["block_status"] == "running" and st["block_started_at"] and st["block_id"] == f"{sid}:0"
    )

    expected_phase = {
        "movement_primer": "practice",
        "retrieval": "review",
        "new_material": "teach",
        "challenge": "challenge",
        "interleaved_review": "review",
        "domain_switch": "practice",
        "recap": "recap",
    }
    for i, t in enumerate(types):
        # "reload": the current session reports exactly the running block
        cur = (await client.get("/api/sessions/current")).json()
        assert cur["state"]["block_index"] == i and cur["state"]["block_status"] == "running"
        assert cur["state"]["phase"] == expected_phase[t], t
        if t == "new_material":
            assert (
                cur["state"]["skill_id"] == s["plan"][i]["node_ids"][0]
            )  # block node = active skill
            # a UI sub-phase checkpoint carries the explicit block index (never a stale render)
            r = await client.post(
                f"/api/sessions/{sid}/checkpoint", json={"phase": "assess", "block_index": i}
            )
            assert r.json()["block_index"] == i and r.json()["block_status"] == "running"
        reason = "skipped" if t == "movement_primer" else "finished"
        r = await client.post(
            "/api/plan/blocks/next",
            json={"session_id": sid, "from_index": i, "reason": reason, "grasp_passed": True},
        )
        st = r.json()
        assert st["allowed"], st
        if i + 1 < len(types):
            assert st["block_index"] == i + 1 and st["block_status"] == "running"
            assert st["phase"] == expected_phase[types[i + 1]]
        else:
            assert (
                st["plan_complete"] and st["block_status"] == "ended" and st["next_index"] is None
            )
    started = await _events(db, sid, "block_started")
    ended = await _events(db, sid, "block_ended")
    assert [e.object_id for e in started] == [f"{sid}:{i}" for i in range(len(types))]
    assert [e.object_id for e in ended] == [f"{sid}:{i}" for i in range(len(types))]
    assert ended[0].result_json["reason"] == "skipped" and ended[0].result_json["switched_early"]
    assert ended[1].result_json["actual_min"] is not None  # server-measured
    practice_events = [e for e in started if e.activity_type == "domain_switch"]
    assert practice_events and practice_events[0].domain == "guitar"
    r = await client.post(f"/api/sessions/{sid}/end", json={"energy_after": 3, "self_report": 4})
    assert r.status_code == 200 and (await client.get("/api/sessions/current")).json() is None
    assert len(await _events(db, sid, "block_ended")) == len(types)  # session end added none


async def test_transitions_are_idempotent_on_retry_and_double_click(
    client: AsyncClient, db: AsyncSession, fake_repo: SqliteHybridRepository
) -> None:
    await _seed(db, fake_repo)
    s = await _start(client)
    sid = s["id"]
    for _ in range(2):  # double-click on start
        r = await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 0})
        assert r.json()["allowed"] and r.json()["block_index"] == 0
    assert len(await _events(db, sid, "block_started")) == 1
    # starting another block while one runs is refused (no silent skip)
    r = await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 1})
    assert r.json()["allowed"] is False and "still running" in r.json()["message"]
    # double-click on "finish": the second call sees the advanced index and changes nothing
    first = (
        await client.post(
            "/api/plan/blocks/next", json={"session_id": sid, "from_index": 0, "reason": "skipped"}
        )
    ).json()
    second = (
        await client.post(
            "/api/plan/blocks/next", json={"session_id": sid, "from_index": 0, "reason": "skipped"}
        )
    ).json()
    assert first["block_index"] == 1 and second["block_index"] == 1
    assert second["message"] == "already advanced"
    assert len(await _events(db, sid, "block_started")) == 2
    assert len(await _events(db, sid, "block_ended")) == 1
    # ending twice writes one event; ending a block that is not running writes none
    r1 = await client.post("/api/plan/blocks/end", json={"session_id": sid, "index": 1})
    r2 = await client.post("/api/plan/blocks/end", json={"session_id": sid, "index": 1})
    assert r1.json()["block_status"] == "ended" and "nothing to end" in r2.json()["message"]
    assert len(await _events(db, sid, "block_ended")) == 2


async def test_grasp_check_blocks_early_switch_and_stop_is_always_allowed(
    client: AsyncClient, db: AsyncSession, fake_repo: SqliteHybridRepository
) -> None:
    await _seed(db, fake_repo)
    s = await _start(client)
    sid = s["id"]
    nm = [b["type"] for b in s["plan"]].index("new_material")
    await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": nm})
    r = await client.post(
        "/api/plan/blocks/next",
        json={"session_id": sid, "from_index": nm, "reason": "switch_early"},
    )
    assert r.json()["allowed"] is False and "grasp" in r.json()["message"]
    assert r.json()["block_index"] == nm and r.json()["block_status"] == "running"  # unchanged
    assert await _events(db, sid, "block_ended") == []
    # save & stop needs no grasp check; ending the session closes the running block exactly once
    r = await client.post(
        "/api/plan/blocks/end",
        json={"session_id": sid, "index": nm, "reason": "save_and_stop", "switched_early": True},
    )
    assert r.json()["allowed"] and r.json()["block_status"] == "ended"
    await client.post(f"/api/sessions/{sid}/end", json={"energy_after": 2, "self_report": 2})
    ended = await _events(db, sid, "block_ended")
    assert len(ended) == 1 and ended[0].result_json["reason"] == "save_and_stop"


async def test_session_end_closes_a_running_block(
    client: AsyncClient, db: AsyncSession, fake_repo: SqliteHybridRepository
) -> None:
    await _seed(db, fake_repo)
    s = await _start(client)
    sid = s["id"]
    await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 1})
    await client.post(f"/api/sessions/{sid}/end", json={"energy_after": 3, "self_report": 3})
    ended = await _events(db, sid, "block_ended")
    assert len(ended) == 1 and ended[0].result_json["reason"] == "session_end"
    st = await blocks.state(db, await ksession.get(db, sid))
    assert st.block_status == "ended"


async def test_timer_extension_and_tutor_turn_keep_block_state(
    client: AsyncClient, db: AsyncSession, fake_repo: SqliteHybridRepository
) -> None:
    await _seed(db, fake_repo)
    s = await _start(client)
    sid = s["id"]
    nm = [b["type"] for b in s["plan"]].index("new_material")
    await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": nm})
    r = await client.post(
        "/api/plan/blocks/extend", json={"session_id": sid, "index": nm, "minutes": 5}
    )
    assert r.json()["timer_extension_min"] == 5
    r = await client.post(
        "/api/plan/blocks/extend", json={"session_id": sid, "index": nm + 1, "minutes": 5}
    )
    assert r.json()["timer_extension_min"] == 5 and "not running" in r.json()["message"]
    started_at = r.json()["block_started_at"]
    # a tutor turn merges into the checkpoint instead of overwriting the block fields
    r = await client.post(
        "/api/tutor/turn", json={"session_id": sid, "text": "explain", "action": "hint"}
    )
    assert r.status_code == 200, r.text
    cur = (await client.get("/api/sessions/current")).json()
    assert cur["checkpoint"]["hint_level"] == 1
    st = cur["state"]
    assert st["block_index"] == nm and st["block_status"] == "running"
    assert st["block_started_at"] == started_at and st["timer_extension_min"] == 5
    assert st["skill_id"] == cur["checkpoint"]["skill_id"]


async def test_review_first_and_new_material_first_semantics(
    client: AsyncClient, db: AsyncSession, fake_repo: SqliteHybridRepository
) -> None:
    await _seed(db, fake_repo)
    s = await _start(client)
    sid = s["id"]
    types = [b["type"] for b in s["plan"]]
    review_ix = types.index("retrieval")
    # review first: the retrieval block starts; earlier blocks are simply not started
    r = await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": review_ix})
    assert r.json()["phase"] == "review"
    r = await client.post(
        "/api/plan/blocks/next", json={"session_id": sid, "from_index": review_ix}
    )
    assert r.json()["block_index"] == review_ix + 1
    started = await _events(db, sid, "block_started")
    assert [e.object_id for e in started] == [f"{sid}:{review_ix}", f"{sid}:{review_ix + 1}"]


async def test_low_capacity_minimum_viable_path(
    client: AsyncClient, db: AsyncSession, fake_repo: SqliteHybridRepository
) -> None:
    await _seed(db, fake_repo)
    s = await _start(client, mode="low_capacity", energy=1)
    types = [b["type"] for b in s["plan"]]
    assert types[0] == "retrieval" and types[-1] == "recap" and "challenge" not in types
    sid = s["id"]
    st = (await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 0})).json()
    assert st["phase"] == "review"
    for i in range(len(types)):
        st = (
            await client.post(
                "/api/plan/blocks/next",
                json={"session_id": sid, "from_index": i, "grasp_passed": True},
            )
        ).json()
        assert st["allowed"], st
    assert st["plan_complete"]


async def test_review_confidence_is_recorded_per_card(
    client: AsyncClient, db: AsyncSession, fake_repo: SqliteHybridRepository
) -> None:
    await _seed(db, fake_repo)
    s = await _start(client)
    sid = s["id"]
    # create two due items via attempts on the active skill
    nxt = (await client.get("/api/assess/next", params={"session_id": sid})).json()
    for conf in (2, 5):
        r = await client.post(
            "/api/assess/attempt",
            json={
                "session_id": sid,
                "assessment_id": nxt["item"]["id"],
                "answer": "x",
                "confidence_pre": conf,
                "latency_ms": 10,
                "hint_count": 0,
            },
        )
        assert r.status_code == 200, r.text
    later = "2031-01-01T00:00:00+00:00"  # FSRS schedules the first review in the future
    due = (
        await client.get(
            "/api/review/due", params={"session_id": sid, "all": "true", "as_of": later}
        )
    ).json()
    assert due["items"], "an attempt schedules a review item"
    item = due["items"][0]["item_id"]
    r = await client.post(
        f"/api/review/{item}",
        params={"as_of": later},
        json={"session_id": sid, "rating": 3, "confidence_pre": 4},
    )
    assert r.status_code == 200, r.text
    reviewed = await _events(db, sid, "reviewed")
    assert reviewed and reviewed[-1].result_json["confidence_pre"] == 4


async def test_next_skill_skips_vocab_decks_but_not_language_lessons(
    db: AsyncSession, learner: models.LearnerProfile
) -> None:
    deck = await practice.vocab_deck(db, "de")
    assert deck.assessment_requirements_json["teachable"] is False
    await practice.add_vocab(db, learner.id, lang="de", word="Haus", translation="house")
    assert await skill_graph.next_skill(db, learner.id) is None  # only a deck: nothing to teach
    lesson = SkillNode(
        domain="language", slug="de-cases-1", title="German cases", description="a real lesson"
    )
    ai = SkillNode(domain="ai_ml", slug="vec-dot", title="Dot product")
    db.add_all([lesson, ai])
    await db.commit()
    nxt = await skill_graph.next_skill(db, learner.id)
    assert nxt is not None and nxt.id != deck.id  # the deck never becomes the next skill
    assert skill_graph.teachable(lesson) and not skill_graph.teachable(deck)
    # a deck created before P1 (no marker) is healed on access
    deck.assessment_requirements_json = {}
    await db.commit()
    healed = await practice.vocab_deck(db, "de")
    assert healed.assessment_requirements_json["teachable"] is False


# ----------------------------------------------------------------------------- review fixes (P1)
async def test_concurrent_next_calls_start_the_next_block_once(
    client: AsyncClient, db: AsyncSession, fake_repo: SqliteHybridRepository
) -> None:
    import asyncio

    await _seed(db, fake_repo)
    s = await _start(client)
    sid = s["id"]
    await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 0})
    body = {"session_id": sid, "from_index": 0, "reason": "skipped"}
    results = await asyncio.gather(
        *[client.post("/api/plan/blocks/next", json=body) for _ in range(3)]
    )
    assert all(r.status_code == 200 for r in results)
    assert {r.json()["block_index"] for r in results} == {1}
    started = await _events(db, sid, "block_started")
    assert [e.object_id for e in started] == [f"{sid}:0", f"{sid}:1"]  # exactly one start of :1
    assert len(await _events(db, sid, "block_ended")) == 1


async def test_checkpoint_endpoint_cannot_move_or_relabel_the_block(
    client: AsyncClient, db: AsyncSession, fake_repo: SqliteHybridRepository
) -> None:
    await _seed(db, fake_repo)
    s = await _start(client)
    sid = s["id"]
    nm = [b["type"] for b in s["plan"]].index("new_material")
    await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 0})
    await client.post(
        "/api/plan/blocks/next", json={"session_id": sid, "from_index": 0, "reason": "skipped"}
    )
    # a stale render posts block 0: refused, state untouched
    r = await client.post(
        f"/api/sessions/{sid}/checkpoint", json={"phase": "review", "block_index": 0}
    )
    assert r.status_code == 409 and r.json()["error"]["code"] == "stale_block"
    # reserved keys in `extra` are dropped silently; a valid sub-phase is kept
    r = await client.post(
        f"/api/sessions/{sid}/checkpoint",
        json={
            "extra": {
                "block_index": 0,
                "block_status": "ended",
                "plan_version": 99,
                "hint_level": 2,
            }
        },
    )
    st = (await client.get("/api/sessions/current")).json()["state"]
    assert st["block_index"] == 1 and st["block_status"] == "running" and st["plan_version"] == 1
    assert r.json()["hint_level"] == 2
    # a phase that does not belong to the running block is refused
    r = await client.post(f"/api/sessions/{sid}/checkpoint", json={"phase": "assess"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "invalid_phase"
    # inside new material teach ↔ assess are the valid sub-phases
    for _ in range(nm - 1):
        r = await client.post(
            "/api/plan/blocks/next",
            json={
                "session_id": sid,
                "from_index": (await client.get("/api/sessions/current")).json()["state"][
                    "block_index"
                ],
            },
        )
    assert (await client.get("/api/sessions/current")).json()["state"]["block_index"] == nm
    r = await client.post(
        f"/api/sessions/{sid}/checkpoint", json={"phase": "assess", "block_index": nm}
    )
    assert r.status_code == 200 and r.json()["phase"] == "assess"


async def test_new_material_needs_recall_evidence_even_when_called_finished(
    client: AsyncClient, db: AsyncSession, fake_repo: SqliteHybridRepository
) -> None:
    await _seed(db, fake_repo)
    s = await _start(client)
    sid = s["id"]
    nm = [b["type"] for b in s["plan"]].index("new_material")
    await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": nm})
    r = await client.post(
        "/api/plan/blocks/next", json={"session_id": sid, "from_index": nm, "reason": "finished"}
    )
    assert r.json()["allowed"] is False and "grasp check" in r.json()["message"]
    # the evidence is read from the event log, not from a client flag (survives a reload)
    nxt = (await client.get("/api/assess/next", params={"session_id": sid})).json()
    r = await client.post(
        "/api/assess/attempt",
        json={
            "session_id": sid,
            "assessment_id": nxt["item"]["id"],
            "answer": "wrong on purpose",
            "confidence_pre": 2,
            "latency_ms": 5,
            "hint_count": 0,
        },
    )
    assert r.status_code == 200, r.text
    r = await client.post(
        "/api/plan/blocks/next", json={"session_id": sid, "from_index": nm, "reason": "finished"}
    )
    assert r.json()["allowed"] and r.json()["block_index"] == nm + 1
    # an out-of-vocabulary reason never reaches the event log
    r = await client.post(
        "/api/plan/blocks/end", json={"session_id": sid, "index": nm + 1, "reason": "whatever"}
    )
    assert r.status_code == 422


async def test_replan_at_energy_one_keeps_the_running_block_and_bumps_plan_version(
    client: AsyncClient, db: AsyncSession, fake_repo: SqliteHybridRepository
) -> None:
    from app.kernel import adaptation

    await _seed(db, fake_repo)
    s = await _start(client)
    sid = s["id"]
    types = [b["type"] for b in s["plan"]]
    ix = types.index("domain_switch")  # optional → would be dropped at energy 1 (old bug)
    await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": ix})
    r = await client.post(
        "/api/plan/replan", json={"session_id": sid, "energy": 1, "from_index": ix}
    )
    assert r.status_code == 200 and r.json()["changed"]
    new_types = [b["type"] for b in r.json()["plan"]["blocks"]]
    assert new_types[ix] == "domain_switch", new_types  # the running block keeps its slot
    card_id = r.json()["proposal_id"]
    learner_id = (await db.execute(select(models.LearnerProfile.id))).scalars().first()
    assert learner_id
    await adaptation.decide(db, learner_id, card_id, "try", session=await ksession.get(db, sid))
    cur = (await client.get("/api/sessions/current")).json()
    st = cur["state"]
    assert st["plan_version"] == 2 and st["block_index"] == ix and st["block_status"] == "running"
    assert st["block"]["type"] == "domain_switch" and cur["plan"][ix]["type"] == "domain_switch"
    r = await client.post("/api/plan/blocks/next", json={"session_id": sid, "from_index": ix})
    ended = await _events(db, sid, "block_ended")
    assert ended[-1].context_json["block_type"] == "domain_switch"  # matches its block_started


async def test_start_after_end_and_continue_after_stop(
    client: AsyncClient, db: AsyncSession, fake_repo: SqliteHybridRepository
) -> None:
    await _seed(db, fake_repo)
    s = await _start(client)
    sid = s["id"]
    await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 0})
    r = await client.post(
        "/api/plan/blocks/end", json={"session_id": sid, "index": 0, "reason": "save_and_stop"}
    )
    assert r.json()["block_status"] == "ended"
    # change of mind: advance without an index continues with the next block, never restarts 0
    r = await client.post("/api/plan/blocks/next", json={"session_id": sid})
    assert r.json()["block_index"] == 1 and r.json()["first_started_index"] == 0
    await client.post(f"/api/sessions/{sid}/end", json={"energy_after": 3, "self_report": 3})
    r = await client.post("/api/plan/blocks/start", json={"session_id": sid, "index": 2})
    assert r.status_code == 400, r.text  # session already ended
    started = await _events(db, sid, "block_started")
    assert [e.object_id for e in started] == [f"{sid}:0", f"{sid}:1"]
