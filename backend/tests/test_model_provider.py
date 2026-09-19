import pytest
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.db.events import EventContext, EventWriter
from app.models_ai import registry
from app.models_ai.budget import Budget
from app.models_ai.fake import FakeProvider
from app.models_ai.gateway import GatewayError, ModelGateway
from app.models_ai.provider import Message, ModelSpec, TaskClass
from app.models_ai.routing import NoModelReady, Router
from app.schemas.common import Mode


class Grade(BaseModel):
    passed: bool
    evidence: str


MSGS = [Message(role="system", content="policy"), Message(role="user", content="hi")]


@pytest.fixture
async def seeded(db: AsyncSession) -> AsyncSession:
    await registry.seed_defaults(
        db, installed_ollama_tags={"llama3.1:8b", "nomic-embed-text:latest", "hosted"}
    )
    return db


def _gateway(
    db: AsyncSession,
    local: FakeProvider,
    hosted: FakeProvider,
    cap: float = 1.0,
    events: EventWriter | None = None,
) -> ModelGateway:
    return ModelGateway(
        db, Router("default"), {"ollama": local, "anthropic": hosted}, Budget(cap), events
    )


async def test_seed_marks_installed_ready(seeded: AsyncSession) -> None:
    rows = {r.id: r.status for r in await registry.list_models(seeded)}
    assert rows["llama31-8b"] == "ready"
    assert rows["nomic-embed-text"] == "ready"
    assert rows["hosted-strong"] == "ready"
    assert rows["gemma3-12b"] == "available"


async def test_router_skips_unready_primary(seeded: AsyncSession) -> None:
    route = await Router("default").resolve(seeded, TaskClass.HINT)
    assert route.chain == ["gemma3-12b", "llama31-8b", "hosted-medium"]
    assert route.registry_id == "llama31-8b" and route.kind == "fallback"

    await registry.set_status(seeded, "llama31-8b", "available")
    await registry.set_status(seeded, "hosted-medium", "available")
    with pytest.raises(NoModelReady):
        await Router("default").resolve(seeded, TaskClass.CHAT)


async def test_router_learner_override(
    seeded: AsyncSession, learner: models.LearnerProfile
) -> None:
    await registry.set_status(seeded, "hosted-medium", "ready", benchmark_json={"latency_ms": 500})
    await registry.assign(seeded, learner.id, TaskClass.CHAT, "hosted-medium")
    route = await Router("default").resolve(seeded, TaskClass.CHAT, learner.id)
    assert route.registry_id == "hosted-medium" and route.override and route.kind == "primary"


async def test_assign_refuses_unbenchmarked(
    seeded: AsyncSession, learner: models.LearnerProfile
) -> None:
    with pytest.raises(ValueError, match="no benchmark"):
        await registry.assign(seeded, learner.id, TaskClass.CHAT, "llama31-8b")
    with pytest.raises(ValueError, match="not ready"):
        await registry.assign(seeded, learner.id, TaskClass.CHAT, "gemma3-12b")


async def test_local_call_logs_zero_cost(seeded: AsyncSession) -> None:
    local, hosted = FakeProvider(text="local"), FakeProvider(text="hosted")
    out = await _gateway(seeded, local, hosted).complete(TaskClass.CHAT, MSGS)
    assert out.result.text == "local" and out.route == "primary" and out.cost_usd == 0.0
    call = (await seeded.execute(select(models.ModelCall))).scalar_one()
    assert call.registry_id == "llama31-8b" and call.task == "chat" and call.cost_usd == 0.0
    assert call.tokens_in == 10 and call.provider == "ollama"  # registry provider, not the adapter


async def test_hosted_call_costs_by_registry_price(seeded: AsyncSession) -> None:
    local, hosted = (
        FakeProvider(text="local"),
        FakeProvider(text="hosted", tokens_in=1000, tokens_out=500),
    )
    out = await _gateway(seeded, local, hosted).complete(TaskClass.GRADE_RUBRIC, MSGS)
    assert out.registry_id == "hosted-strong" and out.result.text == "hosted"
    # 1000 in @ $2/M + 500 out @ $10/M
    assert out.cost_usd == pytest.approx(0.002 + 0.005)


async def test_budget_trips_and_degrades(
    seeded: AsyncSession, learner: models.LearnerProfile
) -> None:
    sess = models.Session(learner_id=learner.id, mode="steady", energy=3)
    seeded.add(sess)
    await seeded.commit()
    events = EventWriter(seeded, EventContext(learner.id, sess.id, Mode.STEADY, 3))
    local, hosted = (
        FakeProvider(text="local"),
        FakeProvider(text="hosted", tokens_in=100_000, tokens_out=0),
    )
    gw = _gateway(seeded, local, hosted, cap=0.30, events=events)

    first = await gw.complete(TaskClass.TUTOR_DEEP, MSGS)  # $0.20, under cap
    assert first.route == "primary" and first.cost_usd == pytest.approx(0.2)
    second = await gw.complete(
        TaskClass.TUTOR_DEEP, MSGS
    )  # $0.40 total, still allowed? no: 0.2 < 0.3
    assert second.cost_usd == pytest.approx(0.2)
    third = await gw.complete(TaskClass.TUTOR_DEEP, MSGS)  # spent 0.4 >= cap -> local, degraded
    assert third.route == "degraded" and third.result.text == "local" and third.cost_usd == 0.0

    ev = (await seeded.execute(select(models.LearningEvent))).scalars().all()
    assert [e.verb for e in ev] == ["degraded"]
    assert ev[0].context_json == {
        "from_alias": "hosted-strong",
        "to_alias": "llama31-8b",
        "reason": "budget",
    }


async def test_invalid_output_escalates_one_tier(
    seeded: AsyncSession, learner: models.LearnerProfile
) -> None:
    await registry.set_status(seeded, "gemma3-12b", "ready")
    events = EventWriter(seeded, EventContext(learner.id, None, Mode.STEADY, 3))
    local = FakeProvider(structured={"passed": True, "evidence": "ok"}, fail_structured_times=1)
    hosted = FakeProvider(structured={"passed": False, "evidence": "hosted"})
    gw = _gateway(seeded, local, hosted, events=events)

    out = await gw.complete(TaskClass.GRADE_SIMPLE, MSGS, response_model=Grade)
    # gemma failed structured -> llama (same fake provider, now succeeds) -> fallback
    assert out.registry_id == "llama31-8b" and out.route == "fallback"
    assert isinstance(out.result.parsed, Grade) and out.result.parsed.passed is True
    ev = (await seeded.execute(select(models.LearningEvent))).scalars().all()
    assert [e.verb for e in ev] == ["invalid_output"]
    calls = (
        (await seeded.execute(select(models.ModelCall).order_by(models.ModelCall.ts)))
        .scalars()
        .all()
    )
    assert [(c.registry_id, c.ok) for c in calls] == [("gemma3-12b", False), ("llama31-8b", True)]


async def test_all_routes_failing_raises(seeded: AsyncSession) -> None:
    local = FakeProvider(fail_times=5)
    with pytest.raises(GatewayError, match="all routes failed"):
        await _gateway(seeded, local, FakeProvider()).complete(TaskClass.CHAT, MSGS)


def test_spec_cost_math() -> None:
    spec = ModelSpec(
        registry_id="x",
        provider="anthropic",
        model="m",
        price_in_per_mtok=1.0,
        price_out_per_mtok=5.0,
    )
    assert spec.cost(1_000_000, 200_000) == pytest.approx(2.0)
    assert spec.hosted
