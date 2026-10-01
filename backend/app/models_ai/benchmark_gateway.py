"""Pin benchmark calls to one model, with normal gateway accounting and no fallback."""

from collections.abc import AsyncIterator
from typing import Any

from pydantic import BaseModel

from app.models_ai.gateway import ModelGateway, StreamHandle
from app.models_ai.provider import Message, ModelSpec, ProviderResult, StreamEvent, TaskClass
from app.models_ai.routing import Router


class BenchmarkRouter(Router):
    def __init__(self, registry_id: str) -> None:
        self.registry_id = registry_id
        self.profile_name = "benchmark"

    def chain_for(self, task: TaskClass, override: str | None = None) -> list[str]:
        return [self.registry_id]


class BenchmarkProvider:
    name = "benchmark"

    def __init__(self, gateway: ModelGateway) -> None:
        self.gateway = gateway

    async def complete(
        self,
        spec: ModelSpec,
        messages: list[Message],
        *,
        response_model: type[BaseModel] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        metadata: dict[str, Any] | None = None,
        max_retries: int = 1,
    ) -> ProviderResult:
        result = await self.gateway.complete(
            TaskClass.CHAT,
            messages,
            response_model=response_model,
            max_tokens=max_tokens,
            temperature=temperature,
            metadata={"purpose": "benchmark", **(metadata or {})},
        )
        return result.result

    async def stream(
        self,
        spec: ModelSpec,
        messages: list[Message],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> AsyncIterator[StreamEvent]:
        async for text in self.gateway.stream(
            TaskClass.CHAT,
            messages,
            handle=StreamHandle(),
            max_tokens=max_tokens,
            temperature=temperature,
            metadata={"purpose": "benchmark"},
        ):
            yield text
