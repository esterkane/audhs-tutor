"""P6 usage/cost accounting: reservations under concurrency, reconcile/release, unknown billing is
never free, duplicate logging suppressed, repair attempts logged, streaming with and without a final
usage chunk, cancellation, configured fallback, stale reservations, the cost view and actionable
routes. Fake providers only."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.db.traces import ModelCallRecord, write_model_call
from app.models_ai import registry, usage
from app.models_ai.budget import Budget, BudgetExceeded, worst_case_usd
from app.models_ai.fake import FakeProvider
from app.models_ai.gateway import GatewayError, ModelGateway, StreamHandle
from app.models_ai.provider import Message, TaskClass
from app.models_ai.routing import Router

MSGS = [Message(role="system", content="policy " * 20), Message(role="user", content="hi")]


class Grade(BaseModel):
    passed: bool


@pytest.fixture
async def seeded(db: AsyncSession) -> AsyncSession:
    await registry.seed_defaults(
        db, installed_ollama_tags={"llama3.1:8b", "nomic-embed-text:latest", "hosted"}
    )
    return db


def _gw(
    db: AsyncSession, local: FakeProvider, hosted: FakeProvider, budget: Budget
) -> ModelGateway:
    return ModelGateway(db, Router("default"), {"ollama": local, "anthropic": hosted}, budget)


async def _calls(db: AsyncSession) -> list[models.ModelCall]:
    return list(
        (await db.execute(select(models.ModelCall).order_by(models.ModelCall.attempt)))
        .scalars()
        .all()
    )


async def _reservations(db: AsyncSession) -> list[models.BudgetReservation]:
    return list((await db.execute(select(models.BudgetReservation))).scalars().all())


async def test_concurrent_hosted_calls_cannot_overshoot_the_cap(
    seeded: AsyncSession,
    session_factory,  # type: ignore[no-untyped-def]
) -> None:
    """Five calls start together. Worst case per attempt = (prompt/3 + 32) tokens in at $2/M +
    1024 out at $10/M ≈ $0.0104; actual $0.007. With a $0.0235 cap the policy alone — never the
    interleaving — admits exactly two: two open reservations ($0.0208) fit, two settled costs plus
    a third bound ($0.0244) do not."""
    lock = asyncio.Lock()
    hosted = FakeProvider(text="hosted", tokens_in=1000, tokens_out=500)  # $0.007 actual
    local = FakeProvider(text="local")
    cap = 0.0235

    async def one() -> str:
        async with session_factory() as db:
            gw = _gw(db, local, hosted, Budget(cap, lock=lock))
            out = await gw.complete(TaskClass.TUTOR_DEEP, MSGS)
            return out.route

    routes = await asyncio.gather(*(one() for _ in range(5)))
    assert sorted(routes) == ["degraded", "degraded", "degraded", "primary", "primary"]
    calls = await _calls(seeded)
    hosted_ok = [c for c in calls if c.provider == "anthropic" and c.ok]
    assert len(hosted_ok) == 2 and all(c.cost_status == "estimated" for c in hosted_ok)
    blocked = [c for c in calls if c.outcome == "blocked"]
    assert len(blocked) >= 3 and all(c.cost_usd == 0 and c.cost_status == "free" for c in blocked)
    spend = await Budget(cap).spend_today(seeded)
    assert spend.open_reservations == 0 and spend.counted == pytest.approx(0.014)
    assert all(r.status == "reconciled" for r in await _reservations(seeded))
    # what the reservations guarantee: admitted worst cases never passed the cap, so the settled
    # cost cannot either
    assert 2 * max(c.reserved_usd for c in hosted_ok) < cap
    assert sum(c.cost_usd for c in hosted_ok) <= cap


async def test_failed_hosted_call_without_usage_is_unknown_not_free(seeded: AsyncSession) -> None:
    hosted = FakeProvider(fail_times=1)
    local = FakeProvider(text="local")
    budget = Budget(1.0)
    out = await _gw(seeded, local, hosted, budget).complete(TaskClass.GRADE_RUBRIC, MSGS)
    # the chain moved on to the next configured model (hosted-medium) after the failure
    assert out.route == "fallback" and out.registry_id != "hosted-strong"
    calls = await _calls(seeded)
    failed = calls[0]
    assert failed.provider == "anthropic" and failed.ok is False and failed.outcome == "error"
    assert failed.cost_status == "unknown" and failed.usage_source == "unavailable"
    assert failed.reserved_usd > 0 and failed.cost_usd == 0.0
    # the unknown call counts toward the cap at its reserved worst case, so it is never "free"
    spend = await budget.spend_today(seeded)
    assert spend.unknown_reserved == pytest.approx(failed.reserved_usd)
    res = {r.registry_id: r for r in await _reservations(seeded)}
    assert len(res) == 2 and all(r.status == "reconciled" for r in res.values())
    # the failed attempt settled at its reserved worst case; the successful fallback at its cost
    assert res["hosted-strong"].settled_usd == pytest.approx(failed.reserved_usd)
    assert res[calls[1].registry_id].settled_usd == pytest.approx(calls[1].cost_usd)
    assert calls[1].request_id == failed.request_id and calls[1].attempt == 2


async def test_duplicate_logging_is_suppressed(seeded: AsyncSession) -> None:
    rec = ModelCallRecord(
        provider="anthropic",
        model="m",
        registry_id="hosted-strong",
        task="chat",
        request_id="req-1",
        attempt=1,
        idempotency_key="req-1:hosted-strong:1",
        cost_usd=0.5,
        cost_status="reported",
        usage_source="reported",
    )
    a = await write_model_call(seeded, rec)
    b = await write_model_call(seeded, rec)
    assert a.id == b.id and len(await _calls(seeded)) == 1
    spend = await Budget(2.0).spend_today(seeded)
    assert spend.reported == pytest.approx(0.5)  # counted once


async def test_repair_attempts_are_logged_and_the_result_is_repaired(
    seeded: AsyncSession,
) -> None:
    local = FakeProvider(structured={"passed": True}, fail_structured_times=1)
    out = await _gw(seeded, local, FakeProvider(), Budget(1.0)).complete(
        TaskClass.CHAT, MSGS, response_model=Grade
    )
    assert isinstance(out.result.parsed, Grade) and out.attempts == 2 and out.route == "primary"
    calls = await _calls(seeded)
    assert [(c.attempt, c.outcome) for c in calls] == [(1, "invalid_output"), (2, "ok")]
    assert (
        calls[0].request_id == calls[1].request_id
        and calls[0].idempotency_key != calls[1].idempotency_key
    )
    # the repair prompt carried the invalid text and the error back to the model
    repair_call = local.calls[-1]
    assert (
        repair_call.messages[-2].role == "assistant"
        and "{not json" in repair_call.messages[-2].content
    )
    assert "did not match the required JSON schema" in repair_call.messages[-1].content


async def test_stream_usage_reported_or_estimated_and_cancellation(seeded: AsyncSession) -> None:
    # (a) a final usage chunk → reported
    local = FakeProvider(text="one two three", stream_usage=(40, 3))
    gw = _gw(seeded, local, FakeProvider(), Budget(1.0))
    h = StreamHandle()
    got = [tok async for tok in gw.stream(TaskClass.CHAT, MSGS, handle=h)]
    assert "".join(got) == "one two three"
    assert h.usage_source == "reported" and (h.tokens_in, h.tokens_out) == (40, 3)
    assert h.cost_status == "free" and h.outcome == "ok" and h.request_id
    # (b) no usage chunk → estimated, flagged as such
    local2 = FakeProvider(text="alpha beta")
    h2 = StreamHandle()
    _ = [
        tok
        async for tok in _gw(seeded, local2, FakeProvider(), Budget(1.0)).stream(
            TaskClass.CHAT, MSGS, handle=h2
        )
    ]
    assert h2.usage_source == "estimated" and h2.tokens_out >= 1
    # (c) the consumer cancels after the first token → the row says so, tokens estimated
    h3 = StreamHandle()
    stream = _gw(seeded, FakeProvider(text="a b c d e"), FakeProvider(), Budget(1.0)).stream(
        TaskClass.CHAT, MSGS, handle=h3
    )
    first = await stream.__anext__()
    await stream.aclose()
    assert first == "a " and h3.outcome == "cancelled"
    calls = await _calls(seeded)
    by_outcome = sorted(c.outcome for c in calls)
    assert by_outcome == ["cancelled", "ok", "ok"]
    cancelled = next(c for c in calls if c.outcome == "cancelled")
    assert cancelled.ok is False and cancelled.error == "cancelled by consumer"
    assert cancelled.metadata_json["estimated_tokens"] is True


async def test_hosted_stream_without_usage_is_estimated_and_reconciled(
    seeded: AsyncSession,
) -> None:
    hosted = FakeProvider(text="deep answer here")
    budget = Budget(1.0)
    h = StreamHandle()
    _ = [
        t
        async for t in _gw(seeded, FakeProvider(), hosted, budget).stream(
            TaskClass.TUTOR_DEEP, MSGS, handle=h
        )
    ]
    assert h.cost_status == "estimated" and h.usage_source == "estimated" and h.cost_usd > 0
    res = await _reservations(seeded)
    assert (
        len(res) == 1
        and res[0].status == "reconciled"
        and res[0].settled_usd == pytest.approx(h.cost_usd)
    )
    assert res[0].model_call_id == h.model_call_id


async def test_configured_fallback_is_visible(seeded: AsyncSession) -> None:
    await registry.set_status(
        seeded, "gemma3-12b", "available"
    )  # primary for explain_simple? use chain
    local = FakeProvider(text="local")
    out = await _gw(seeded, local, FakeProvider(), Budget(1.0)).complete(
        TaskClass.GRADE_SIMPLE, MSGS
    )
    # gemma3-12b (primary) is not ready → llama31-8b answers as the configured fallback
    assert out.registry_id == "llama31-8b" and out.route == "fallback"
    call = (await _calls(seeded))[0]
    assert (
        call.route == "fallback" and call.cost_status == "free" and call.usage_source == "reported"
    )


async def test_stale_reservations_expire_and_release(seeded: AsyncSession) -> None:
    budget = Budget(0.02)
    stale = models.BudgetReservation(
        request_id="old",
        registry_id="hosted-strong",
        task="chat",
        amount_usd=0.019,
        status="open",
        expires_at=(datetime.now(UTC) - timedelta(minutes=1)).isoformat(timespec="milliseconds"),
    )
    seeded.add(stale)
    await seeded.commit()
    # counted while open-and-unexpired only: the stale one is ignored and marked expired
    spend = await budget.spend_today(seeded)
    assert spend.open_reservations == 0
    res = await budget.reserve(
        seeded,
        request_id="new",
        registry_id="hosted-strong",
        task="chat",
        amount_usd=0.01,
        learner_id=None,
    )
    await seeded.refresh(stale)
    assert stale.status == "expired" and res.status == "open"
    with pytest.raises(BudgetExceeded):
        await budget.reserve(
            seeded,
            request_id="new2",
            registry_id="hosted-strong",
            task="chat",
            amount_usd=0.01,
            learner_id=None,
        )
    await budget.release(seeded, res)
    assert res.status == "released" and res.settled_usd == 0.0
    assert (await budget.spend_today(seeded)).counted == 0.0


def test_worst_case_bounds_output_by_max_tokens() -> None:
    small = worst_case_usd(2.0, 10.0, prompt_chars=300, max_tokens=100, n_messages=2)
    big = worst_case_usd(2.0, 10.0, prompt_chars=300, max_tokens=1000, n_messages=2)
    assert big > small and big == pytest.approx((100 + 32) / 1e6 * 2.0 + 1000 / 1e6 * 10.0)


async def test_reported_cost_wins_even_with_zero_tokens_and_below_estimate(
    seeded: AsyncSession,
) -> None:
    # prompt caching: the provider bills less than the registry estimate — the row says so
    hosted = FakeProvider(text="h", tokens_in=100_000, tokens_out=0, reported_cost_usd=0.02)
    out = await _gw(seeded, FakeProvider(), hosted, Budget(1.0)).complete(
        TaskClass.TUTOR_DEEP, MSGS
    )
    assert out.cost_status == "reported" and out.cost_usd == pytest.approx(0.02)
    call = (await _calls(seeded))[0]
    assert call.metadata_json["registry_estimate_usd"] == pytest.approx(0.2)
    # a reported cost with no token counts is still a reported cost, not "unknown"
    hosted2 = FakeProvider(text="h", tokens_in=0, tokens_out=0, reported_cost_usd=0.001)
    out2 = await _gw(seeded, FakeProvider(), hosted2, Budget(1.0)).complete(
        TaskClass.TUTOR_DEEP, MSGS
    )
    assert out2.cost_status == "reported" and out2.usage_source == "unavailable"


async def test_hosted_repairs_reserve_per_attempt(seeded: AsyncSession) -> None:
    hosted = FakeProvider(structured={"passed": True}, fail_structured_times=2)
    budget = Budget(1.0)
    out = await _gw(seeded, FakeProvider(), hosted, budget).complete(
        TaskClass.GRADE_RUBRIC, MSGS, response_model=Grade
    )
    assert out.attempts == 3 and out.registry_id == "hosted-strong"
    res = await _reservations(seeded)
    assert len(res) == 3 and all(r.status == "reconciled" for r in res)
    calls = await _calls(seeded)
    assert [c.outcome for c in calls] == ["invalid_output", "invalid_output", "ok"]
    # the failed structured attempts had usage → their cost is estimated, not unknown
    assert all(c.cost_status == "estimated" and c.cost_usd > 0 for c in calls[:2])
    assert calls[2].metadata_json["repair"] == 2


async def test_partial_stream_leaves_a_partial_row(seeded: AsyncSession) -> None:
    local = FakeProvider(text="one two three four", fail_after_words=2)
    h = StreamHandle()
    got: list[str] = []
    with pytest.raises(GatewayError, match="broke mid-way"):
        async for tok in _gw(seeded, local, FakeProvider(), Budget(1.0)).stream(
            TaskClass.CHAT, MSGS, handle=h
        ):
            got.append(tok)
    assert "".join(got) == "one two "
    call = (await _calls(seeded))[0]
    assert call.outcome == "partial" and call.ok is False and h.outcome == "partial"
    assert h.model_call_id == call.id


async def test_client_disconnect_mid_stream_is_a_cancelled_row(seeded: AsyncSession) -> None:
    local = FakeProvider(text="a b c d e f", stream_delay_s=0.01)
    h = StreamHandle()
    gw = _gw(seeded, local, FakeProvider(), Budget(1.0))

    async def consume() -> None:
        async for _ in gw.stream(TaskClass.CHAT, MSGS, handle=h):
            pass

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.025)  # a couple of words in
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    call = (await _calls(seeded))[0]
    assert call.outcome == "cancelled" and "disconnected" in (call.error or "")


async def test_expire_stale_reports_how_many(seeded: AsyncSession) -> None:
    budget = Budget(1.0)
    for i in range(2):
        seeded.add(
            models.BudgetReservation(
                request_id=f"old{i}",
                registry_id="hosted-strong",
                task="chat",
                amount_usd=0.01,
                status="open",
                expires_at=(datetime.now(UTC) - timedelta(minutes=1)).isoformat(
                    timespec="milliseconds"
                ),
            )
        )
    await seeded.commit()
    assert await budget.expire_stale(seeded) == 2
    assert await budget.expire_stale(seeded) == 0


async def test_all_routes_failing_still_leaves_rows(seeded: AsyncSession) -> None:
    local = FakeProvider(fail_times=5)
    with pytest.raises(GatewayError):
        await _gw(seeded, local, FakeProvider(), Budget(1.0)).complete(TaskClass.CHAT, MSGS)
    calls = await _calls(seeded)
    assert calls and all(c.outcome == "error" and c.cost_status == "free" for c in calls)


async def test_cost_view_and_actionable_routes(client: AsyncClient, seeded: AsyncSession) -> None:
    hosted = FakeProvider(text="h", tokens_in=1000, tokens_out=100, reported_cost_usd=0.004)
    gw = _gw(seeded, FakeProvider(text="l"), hosted, Budget(1.0))
    await gw.complete(TaskClass.GRADE_RUBRIC, MSGS)
    await gw.complete(TaskClass.CHAT, MSGS)
    hosted.fail_times = 1
    await gw.complete(TaskClass.GRADE_RUBRIC, MSGS)  # error → unknown, then local fallback
    rep = await usage.cost_report(seeded, Budget(1.0))
    d = usage.report_dict(rep)
    # two hosted successes reported $0.004 each (the second grade_rubric fell back to hosted-medium)
    assert d["today"]["reported"] == pytest.approx(0.008)
    assert d["today"]["unknown_reserved"] > 0 and d["window"]["failed_calls"] == 1
    assert d["window"]["cancelled_calls"] == 0
    assert d["window"]["retried_requests"] == 1  # the failed request had a second attempt
    tasks = {b["key"]: b for b in d["by_task"]}
    assert tasks["grade_rubric"]["failed"] == 1 and tasks["grade_rubric"]["unknown_usd"] > 0
    assert d["recent_failures"][0]["cost_status"] == "unknown"
    r = await client.get("/api/models/costs")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["daily_cap_usd"] == 1.0 and "counted" in body["today"]
    # a task whose chain has nothing ready gets a problem + one concrete action
    r = await client.get("/api/models/routing")
    rows = {row["task"]: row for row in r.json()["routes"]}
    assert rows["chat"]["problem"] is None
    unready = next(row for row in rows.values() if row["resolved"] is None)
    assert unready["problem"] and unready["action"]
