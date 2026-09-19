"""ModelGateway: the one entry point the orchestrator uses for LLM calls.

resolve route -> (budget check for hosted) -> provider.complete -> model_call row (+ events).
Failures walk the fallback chain: structured-output failure emits `invalid_output`, a hosted call
blocked by the budget emits `degraded`, transport errors are logged as ok=False.
"""

from collections.abc import AsyncGenerator
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.events import EventWriter, Verb
from app.db.traces import ModelCallRecord, write_model_call
from app.models_ai import registry
from app.models_ai.budget import Budget, BudgetExceeded
from app.models_ai.provider import (
    Message,
    ModelProvider,
    ModelSpec,
    ProviderError,
    ProviderResult,
    StructuredOutputError,
    TaskClass,
)
from app.models_ai.routing import NoModelReady, Router
from app.schemas.common import Actor, ObjectType


class GatewayResult(BaseModel):
    result: ProviderResult
    model_call_id: str
    registry_id: str
    route: str  # primary | fallback | degraded
    cost_usd: float
    hosted: bool = False


class GatewayError(Exception):
    pass


class StreamHandle:
    """Filled in after a `stream()` finishes so the caller can link traces to the model_call row."""

    def __init__(self) -> None:
        self.model_call_id: str | None = None
        self.registry_id: str | None = None
        self.route: str | None = None
        self.tokens_in: int = 0
        self.tokens_out: int = 0
        self.cached_tokens: int = 0
        self.latency_ms: int = 0


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
        route = await self.router.resolve(self.db, task, learner_id)
        chain = route.chain[route.position :]
        degraded = False
        errors: list[str] = []
        meta = {**(metadata or {}), "task": str(task), "session_id": session_id}

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
            if spec.hosted:
                try:
                    await self.budget.check(self.db)
                except BudgetExceeded as e:
                    errors.append(str(e))
                    nxt = chain[pos + 1] if pos + 1 < len(chain) else None
                    await self._emit(
                        Verb.DEGRADED,
                        rid,
                        {"from_alias": rid, "to_alias": nxt, "reason": "budget"},
                    )
                    degraded = True
                    continue
            try:
                result = await provider.complete(
                    spec,
                    messages,
                    response_model=response_model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    metadata=meta,
                )
            except StructuredOutputError as e:
                errors.append(f"{rid}: {e}")
                await self._emit(
                    Verb.INVALID_OUTPUT,
                    rid,
                    {"task": str(task), "model": rid, "attempts": e.attempts},
                )
                await self._log(
                    spec,
                    task,
                    "primary" if pos == 0 else "fallback",
                    None,
                    learner_id,
                    session_id,
                    meta,
                    error=str(e),
                )
                continue
            except ProviderError as e:
                errors.append(f"{rid}: {e}")
                await self._log(
                    spec,
                    task,
                    "primary" if pos == 0 else "fallback",
                    None,
                    learner_id,
                    session_id,
                    meta,
                    error=str(e),
                )
                continue

            kind = (
                "degraded" if degraded else ("primary" if route.position + pos == 0 else "fallback")
            )
            call = await self._log(spec, task, kind, result, learner_id, session_id, meta)
            return GatewayResult(
                result=result,
                model_call_id=call.id,
                registry_id=rid,
                route=kind,
                cost_usd=call.cost_usd,
                hosted=spec.hosted,
            )

        raise GatewayError(f"{task}: all routes failed: {errors}")

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
        """Stream tokens from the first ready model in the chain; token counts are estimated
        (chars/4) because streams carry no usage. Budget and readiness rules as in complete().
        The model_call row is always written, also when the consumer aborts mid-stream."""
        import time

        if events is not None:
            self.events = events
        route = await self.router.resolve(self.db, task, learner_id)
        chain = route.chain[route.position :]
        errors: list[str] = []
        degraded = False
        meta = {
            **(metadata or {}),
            "task": str(task),
            "session_id": session_id,
            "estimated_tokens": True,
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
            if spec.hosted:
                try:
                    await self.budget.check(self.db)
                except BudgetExceeded as e:
                    errors.append(str(e))
                    nxt = chain[pos + 1] if pos + 1 < len(chain) else None
                    await self._emit(
                        Verb.DEGRADED, rid, {"from_alias": rid, "to_alias": nxt, "reason": "budget"}
                    )
                    degraded = True
                    continue
            kind = (
                "degraded" if degraded else ("primary" if route.position + pos == 0 else "fallback")
            )
            t0 = time.perf_counter()
            out_chars = 0
            started = False
            failure: str | None = None
            try:
                async for tok in provider.stream(
                    spec, messages, max_tokens=max_tokens, temperature=temperature
                ):
                    started = True
                    out_chars += len(tok)
                    yield tok
            except ProviderError as e:
                failure = str(e)
                errors.append(f"{rid}: {e}")
                if not started:
                    await self._log(
                        spec, task, kind, None, learner_id, session_id, meta, error=failure
                    )
                    continue
                raise GatewayError(f"{task}: stream from {rid} broke mid-way: {e}") from e
            except GeneratorExit:
                failure = "cancelled by consumer"
                raise
            finally:
                if started:
                    result = ProviderResult(
                        text="",
                        tokens_in=prompt_chars // 4,
                        tokens_out=max(1, out_chars // 4),
                        latency_ms=int((time.perf_counter() - t0) * 1000),
                        model=spec.model,
                        provider=spec.provider,
                    )
                    call = await self._log(
                        spec, task, kind, result, learner_id, session_id, meta, error=failure
                    )
                    handle.model_call_id, handle.registry_id, handle.route = call.id, rid, kind
                    handle.tokens_in, handle.tokens_out = result.tokens_in, result.tokens_out
                    handle.latency_ms = result.latency_ms
            return
        raise GatewayError(f"{task}: all routes failed: {errors}")

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
        error: str | None = None,
    ) -> Any:
        cost = 0.0
        if result is not None and spec.hosted:
            cost = spec.cost(result.tokens_in, result.tokens_out)
            if result.reported_cost_usd:
                cost = max(cost, result.reported_cost_usd)
        rec = ModelCallRecord(
            provider=spec.provider,
            model=spec.model,
            registry_id=spec.registry_id,
            task=str(task),
            route=route,
            tokens_in=result.tokens_in if result else 0,
            tokens_out=result.tokens_out if result else 0,
            cached_tokens=result.cached_tokens if result else 0,
            cost_usd=cost,
            latency_ms=result.latency_ms if result else 0,
            cached=bool(result and result.cached_tokens),
            ok=error is None,
            error=error,
            metadata=meta,
            learner_id=learner_id,
            session_id=session_id,
        )
        return await write_model_call(self.db, rec)


__all__ = ["GatewayError", "GatewayResult", "ModelGateway", "NoModelReady", "StreamHandle"]
