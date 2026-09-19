"""ModelGateway: the one entry point the orchestrator uses for LLM calls.

resolve route -> (budget check for hosted) -> provider.complete -> model_call row (+ events).
Failures walk the fallback chain: structured-output failure emits `invalid_output`, a hosted call
blocked by the budget emits `degraded`, transport errors are logged as ok=False.
"""

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


class GatewayError(Exception):
    pass


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
    ) -> GatewayResult:
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
            )

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


__all__ = ["GatewayError", "GatewayResult", "ModelGateway", "NoModelReady"]
