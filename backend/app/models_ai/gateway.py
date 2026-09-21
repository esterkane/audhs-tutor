"""ModelGateway: the one entry point the orchestrator uses for LLM calls.

resolve route → (reserve budget for hosted) → provider attempt(s) → model_call row per attempt
(+ events). One gateway call = one `request_id`; every provider attempt — fallback model,
structured-output repair, blocked-by-budget — is its own `model_call` row with `attempt` 1..n and a
unique idempotency key, so failures stay visible and nothing is counted twice (P6).

Usage/cost honesty: `usage_source` says where the token counts came from (provider-reported,
estimated from characters, unavailable); `cost_status` says what the cost figure is (free for local,
reported, estimated = tokens × registry price, unknown = a failed hosted call with no usage — counted
at its reserved worst case, never as free). Local fallback (`route=fallback`) and budget degradation
(`route=degraded`, `degraded` event) are recorded on the row and surfaced to the learner.
"""

import asyncio
import re
import time
from collections.abc import AsyncGenerator
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import ULID

from app.db.events import EventWriter, Verb
from app.db.models import BudgetReservation, ModelRegistry
from app.db.traces import ModelCallRecord, write_model_call
from app.models_ai import registry
from app.models_ai.budget import Budget, BudgetExceeded, worst_case_usd
from app.models_ai.provider import (
    Message,
    ModelProvider,
    ModelSpec,
    ProviderError,
    ProviderResult,
    StreamUsage,
    StructuredOutputError,
    TaskClass,
)
from app.models_ai.routing import NoModelReady, Router
from app.schemas.common import Actor, ObjectType

MAX_REPAIRS = 2  # structured output: 1 attempt + up to 2 repairs per model, then escalate
REPAIR_INSTRUCTION = (
    "Your previous reply did not match the required JSON schema: {errors}\n"
    "Reply again with only a JSON object that matches the schema. No prose."
)
_INPUT_VALUE = re.compile(r"input_value=.*?(?=, input_type=|\n|$)", re.S)


def repair_errors(text: str) -> str:
    """Validation messages only: the model's own reply text (`input_value=…`) never comes back in
    a user-role turn (ADR-0008: model output has no user authority)."""
    return _INPUT_VALUE.sub("input_value=<omitted>", text)[:1500]


class GatewayResult(BaseModel):
    result: ProviderResult
    model_call_id: str
    registry_id: str
    route: str  # primary | fallback | degraded
    cost_usd: float
    hosted: bool = False
    request_id: str = ""
    attempts: int = 1
    usage_source: str = "unavailable"
    cost_status: str = "free"


class GatewayError(Exception):
    pass


class StreamHandle:
    """Filled in after a `stream()` finishes so the caller can link traces to the model_call row."""

    def __init__(self) -> None:
        self.model_call_id: str | None = None
        self.registry_id: str | None = None
        self.route: str | None = None
        self.request_id: str | None = None
        self.tokens_in: int = 0
        self.tokens_out: int = 0
        self.cached_tokens: int = 0
        self.latency_ms: int = 0
        self.usage_source: str = "unavailable"
        self.cost_status: str = "free"
        self.cost_usd: float = 0.0
        self.outcome: str = "ok"


def _accounting(
    spec: ModelSpec, tokens_in: int, tokens_out: int, reported: float | None, *, usage_source: str
) -> tuple[float, str]:
    """(cost_usd, cost_status) for a completed hosted/local attempt with the given usage. A
    provider-reported cost is taken as is (prompt caching makes it legitimately *lower* than the
    registry estimate); the registry estimate is kept in the row's metadata for comparison."""
    if not spec.hosted:
        return 0.0, "free"
    if reported is not None:
        return round(reported, 6), "reported"
    if usage_source == "unavailable":
        return 0.0, "unknown"
    return spec.cost(tokens_in, tokens_out), "estimated"


class ModelGateway:
    def __init__(
        self,
        db: AsyncSession,
        router: Router,
        providers: dict[str, ModelProvider],
        budget: Budget,
        events: EventWriter | None = None,
    ) -> None:
        self.db = db
        self.router = router
        self.providers = providers
        self.budget = budget
        self.events = events

    async def _emit(self, verb: Verb, object_id: str, context: dict[str, Any]) -> None:
        if self.events is not None:
            await self.events.emit(
                verb, ObjectType.MODEL, object_id, actor=Actor.SYSTEM, context=context
            )

    # ------------------------------------------------------------------ helpers
    async def _ready(self, chain: list[str]) -> set[str]:
        rows = await self.db.execute(
            select(ModelRegistry.id).where(
                ModelRegistry.id.in_(chain), ModelRegistry.status == "ready"
            )
        )
        return {str(r) for r in rows.scalars()}

    async def _reserve(
        self,
        spec: ModelSpec,
        *,
        request_id: str,
        task: TaskClass,
        learner_id: str | None,
        prompt_chars: int,
        max_tokens: int,
        n_messages: int,
        next_rid: str | None,
    ) -> tuple[BudgetReservation | None, float, bool]:
        """(reservation, worst_case_usd, blocked). Local models never reserve."""
        if not spec.hosted:
            return None, 0.0, False
        bound = worst_case_usd(
            spec.price_in_per_mtok, spec.price_out_per_mtok, prompt_chars, max_tokens, n_messages
        )
        try:
            res = await self.budget.reserve(
                self.db,
                request_id=request_id,
                registry_id=spec.registry_id,
                task=str(task),
                amount_usd=bound,
                learner_id=learner_id,
            )
        except BudgetExceeded:
            await self._emit(
                Verb.DEGRADED,
                spec.registry_id,
                {"from_alias": spec.registry_id, "to_alias": next_rid, "reason": "budget"},
            )
            return None, bound, True
        return res, bound, False

    # ------------------------------------------------------------------ complete
    async def complete(
        self,
        task: TaskClass,
        messages: list[Message],
        *,
        response_model: type[BaseModel] | None = None,
        learner_id: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        events: EventWriter | None = None,
    ) -> GatewayResult:
        if events is not None:
            self.events = events
        request_id = str(ULID())
        route = await self.router.resolve(self.db, task, learner_id)
        chain = route.chain[route.position :]
        ready = await self._ready(chain)
        degraded = False
        errors: list[str] = []
        attempt = 0
        meta = {
            **(metadata or {}),
            "task": str(task),
            "session_id": session_id,
            "request_id": request_id,
        }

        for pos, rid in enumerate(chain):
            try:
                spec: ModelSpec = await registry.get_spec(self.db, rid)
            except KeyError as e:
                errors.append(str(e))
                continue
            row = await registry.get_row(self.db, rid)
            if row.status != "ready":
                continue
            provider = self.providers.get(spec.provider)
            if provider is None:
                errors.append(f"{rid}: no provider for {spec.provider}")
                continue
            kind = (
                "degraded" if degraded else ("primary" if route.position + pos == 0 else "fallback")
            )
            msgs = list(messages)
            repairs = 0
            while True:
                reservation, bound, blocked = await self._reserve(
                    spec,
                    request_id=request_id,
                    task=task,
                    learner_id=learner_id,
                    prompt_chars=sum(len(m.content) for m in msgs),
                    max_tokens=max_tokens,
                    n_messages=len(msgs),
                    next_rid=next((r for r in chain[pos + 1 :] if r in ready), None),
                )
                attempt += 1
                if blocked:
                    errors.append(f"{rid}: daily hosted budget reached")
                    degraded = True
                    await self._log(
                        spec,
                        task,
                        kind,
                        None,
                        learner_id,
                        session_id,
                        meta,
                        request_id=request_id,
                        attempt=attempt,
                        outcome="blocked",
                        usage_source="unavailable",
                        cost_status="free",
                        reserved_usd=bound,
                        error="budget: daily hosted cap reached before the call",
                        reservation=reservation,
                    )
                    break
                try:
                    result = await provider.complete(
                        spec,
                        msgs,
                        response_model=response_model,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        metadata=meta,
                        max_retries=1,
                    )
                except StructuredOutputError as e:
                    errors.append(f"{rid}: {e}")
                    source = "reported" if (e.tokens_in or e.tokens_out) else "unavailable"
                    cost, status = _accounting(
                        spec, e.tokens_in, e.tokens_out, None, usage_source=source
                    )
                    call = await self._log(
                        spec,
                        task,
                        kind,
                        ProviderResult(
                            tokens_in=e.tokens_in,
                            tokens_out=e.tokens_out,
                            cached_tokens=e.cached_tokens,
                            model=spec.model,
                            provider=spec.provider,
                        ),
                        learner_id,
                        session_id,
                        {**meta, "repair": repairs},
                        request_id=request_id,
                        attempt=attempt,
                        outcome="invalid_output",
                        usage_source=source,
                        cost_status=status,
                        cost_usd=cost,
                        reserved_usd=bound,
                        error=str(e)[:500],
                        reservation=reservation,
                    )
                    if repairs < MAX_REPAIRS:
                        repairs += 1
                        msgs = [
                            *msgs,
                            *(
                                [Message(role="assistant", content=e.last_text[:4000])]
                                if e.last_text
                                else []
                            ),
                            Message(
                                role="user",
                                content=REPAIR_INSTRUCTION.format(errors=repair_errors(str(e))),
                            ),
                        ]
                        continue
                    await self._emit(
                        Verb.INVALID_OUTPUT,
                        rid,
                        {"task": str(task), "model": rid, "attempts": repairs + 1},
                    )
                    break
                except ProviderError as e:
                    errors.append(f"{rid}: {e}")
                    cost, status = _accounting(spec, 0, 0, None, usage_source="unavailable")
                    call = await self._log(
                        spec,
                        task,
                        kind,
                        None,
                        learner_id,
                        session_id,
                        meta,
                        request_id=request_id,
                        attempt=attempt,
                        outcome="error",
                        usage_source="unavailable",
                        cost_status=status,
                        reserved_usd=bound,
                        error=str(e)[:500],
                        reservation=reservation,
                    )
                    break
                source = "reported" if (result.tokens_in or result.tokens_out) else "unavailable"
                cost, status = _accounting(
                    spec,
                    result.tokens_in,
                    result.tokens_out,
                    result.reported_cost_usd,
                    usage_source=source,
                )
                call = await self._log(
                    spec,
                    task,
                    kind,
                    result,
                    learner_id,
                    session_id,
                    {
                        **meta,
                        **({"repair": repairs} if repairs else {}),
                        **(
                            {
                                "registry_estimate_usd": spec.cost(
                                    result.tokens_in, result.tokens_out
                                )
                            }
                            if spec.hosted
                            else {}
                        ),
                    },
                    request_id=request_id,
                    attempt=attempt,
                    outcome="ok",
                    usage_source=source,
                    cost_status=status,
                    cost_usd=cost,
                    reserved_usd=bound,
                    reservation=reservation,
                )
                return GatewayResult(
                    result=result,
                    model_call_id=call.id,
                    registry_id=rid,
                    route=kind,
                    cost_usd=cost,
                    hosted=spec.hosted,
                    request_id=request_id,
                    attempts=attempt,
                    usage_source=source,
                    cost_status=status,
                )

        raise GatewayError(f"{task}: all routes failed: {errors}")

    # ------------------------------------------------------------------ stream
    async def stream(
        self,
        task: TaskClass,
        messages: list[Message],
        *,
        handle: StreamHandle,
        learner_id: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        max_tokens: int = 700,
        temperature: float = 0.3,
        events: EventWriter | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from the first ready model in the chain. Usage comes from the provider's
        final usage chunk when it sends one (`usage_source=reported`); otherwise tokens are
        estimated as chars/4 (`estimated`). Budget and readiness rules as in complete(). The
        model_call row is always written — also when the consumer cancels (`outcome=cancelled`) or
        the stream breaks mid-way (`partial`)."""
        if events is not None:
            self.events = events
        request_id = str(ULID())
        handle.request_id = request_id
        route = await self.router.resolve(self.db, task, learner_id)
        chain = route.chain[route.position :]
        ready = await self._ready(chain)
        errors: list[str] = []
        degraded = False
        attempt = 0
        meta = {
            **(metadata or {}),
            "task": str(task),
            "session_id": session_id,
            "request_id": request_id,
        }
        prompt_chars = sum(len(m.content) for m in messages)
        for pos, rid in enumerate(chain):
            try:
                row = await registry.get_row(self.db, rid)
            except KeyError as e:
                errors.append(str(e))
                continue
            if row.status != "ready":
                continue
            spec = registry.spec_from_row(row)
            provider = self.providers.get(spec.provider)
            if provider is None:
                errors.append(f"{rid}: no provider for {spec.provider}")
                continue
            kind = (
                "degraded" if degraded else ("primary" if route.position + pos == 0 else "fallback")
            )
            reservation, bound, blocked = await self._reserve(
                spec,
                request_id=request_id,
                task=task,
                learner_id=learner_id,
                prompt_chars=prompt_chars,
                max_tokens=max_tokens,
                n_messages=len(messages),
                next_rid=next((r for r in chain[pos + 1 :] if r in ready), None),
            )
            attempt += 1
            if blocked:
                errors.append(f"{rid}: daily hosted budget reached")
                degraded = True
                await self._log(
                    spec,
                    task,
                    kind,
                    None,
                    learner_id,
                    session_id,
                    meta,
                    request_id=request_id,
                    attempt=attempt,
                    outcome="blocked",
                    usage_source="unavailable",
                    cost_status="free",
                    reserved_usd=bound,
                    error="budget: daily hosted cap reached before the call",
                    reservation=reservation,
                )
                continue
            t0 = time.perf_counter()
            out_chars = 0
            started = False
            usage: StreamUsage | None = None
            failure: str | None = None
            outcome = "ok"
            logged = False
            try:
                async for ev in provider.stream(
                    spec, messages, max_tokens=max_tokens, temperature=temperature
                ):
                    if isinstance(ev, StreamUsage):
                        usage = ev
                        continue
                    started = True
                    out_chars += len(ev)
                    yield ev
            except ProviderError as e:
                failure = str(e)
                errors.append(f"{rid}: {e}")
                if not started:
                    cost, status = _accounting(spec, 0, 0, None, usage_source="unavailable")
                    call = await self._log(
                        spec,
                        task,
                        kind,
                        None,
                        learner_id,
                        session_id,
                        meta,
                        request_id=request_id,
                        attempt=attempt,
                        outcome="error",
                        usage_source="unavailable",
                        cost_status=status,
                        reserved_usd=bound,
                        error=failure[:500],
                        reservation=reservation,
                    )
                    logged = True
                    continue
                outcome = "partial"
                raise GatewayError(f"{task}: stream from {rid} broke mid-way: {e}") from e
            except GeneratorExit:
                failure = "cancelled by consumer"
                outcome = "cancelled"
                raise
            except asyncio.CancelledError:
                failure = "cancelled (client disconnected)"
                outcome = "cancelled"
                raise
            finally:
                if (started or usage is not None) and not logged:
                    if usage is not None:
                        source = "reported"
                        tin, tout, cached = usage.tokens_in, usage.tokens_out, usage.cached_tokens
                        reported = usage.reported_cost_usd
                    else:
                        source = "estimated"
                        tin, tout, cached = prompt_chars // 4, max(1, out_chars // 4), 0
                        reported = None
                    cost, status = _accounting(spec, tin, tout, reported, usage_source=source)
                    result = ProviderResult(
                        text="",
                        tokens_in=tin,
                        tokens_out=tout,
                        cached_tokens=cached,
                        latency_ms=int((time.perf_counter() - t0) * 1000),
                        model=spec.model,
                        provider=spec.provider,
                        reported_cost_usd=reported,
                    )
                    call = await self._log(
                        spec,
                        task,
                        kind,
                        result,
                        learner_id,
                        session_id,
                        {**meta, "estimated_tokens": source == "estimated"},
                        request_id=request_id,
                        attempt=attempt,
                        outcome=outcome,
                        usage_source=source,
                        cost_status=status,
                        cost_usd=cost,
                        reserved_usd=bound,
                        error=failure,
                        reservation=reservation,
                    )
                    handle.model_call_id, handle.registry_id, handle.route = call.id, rid, kind
                    handle.tokens_in, handle.tokens_out = result.tokens_in, result.tokens_out
                    handle.cached_tokens = result.cached_tokens
                    handle.latency_ms = result.latency_ms
                    handle.usage_source, handle.cost_status = source, status
                    handle.cost_usd, handle.outcome = cost, outcome
            return
        raise GatewayError(f"{task}: all routes failed: {errors}")

    # ------------------------------------------------------------------ log
    async def _log(
        self,
        spec: ModelSpec,
        task: TaskClass,
        route: str,
        result: ProviderResult | None,
        learner_id: str | None,
        session_id: str | None,
        meta: dict[str, Any],
        *,
        request_id: str,
        attempt: int,
        outcome: str,
        usage_source: str,
        cost_status: str,
        cost_usd: float = 0.0,
        reserved_usd: float = 0.0,
        error: str | None = None,
        reservation: BudgetReservation | None = None,
    ) -> Any:
        rec = ModelCallRecord(
            provider=spec.provider,
            model=spec.model,
            registry_id=spec.registry_id,
            task=str(task),
            route=route,
            tokens_in=result.tokens_in if result else 0,
            tokens_out=result.tokens_out if result else 0,
            cached_tokens=result.cached_tokens if result else 0,
            cost_usd=cost_usd,
            latency_ms=result.latency_ms if result else 0,
            cached=bool(result and result.cached_tokens),
            ok=outcome == "ok",
            error=error,
            metadata=meta,
            learner_id=learner_id,
            session_id=session_id,
            request_id=request_id,
            attempt=attempt,
            idempotency_key=f"{request_id}:{spec.registry_id}:{attempt}",
            outcome=outcome,
            usage_source=usage_source,
            cost_status=cost_status,
            reserved_usd=reserved_usd if spec.hosted else 0.0,
        )
        # the row and its reservation settle in ONE commit: no window in which both the open
        # reservation and the logged cost count toward the cap
        amount = reservation.amount_usd if reservation is not None else 0.0
        call = await write_model_call(self.db, rec, commit=False)
        if reservation is not None:
            reservation.status = "reconciled"
            reservation.settled_usd = amount if cost_status == "unknown" else round(cost_usd, 6)
            reservation.model_call_id = call.id
        await self.db.commit()
        return call


__all__ = ["GatewayError", "GatewayResult", "ModelGateway", "NoModelReady", "StreamHandle"]
