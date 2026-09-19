"""FakeProvider for tests and offline evals: canned outputs, scripted failures, call log."""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from app.models_ai.provider import (
    Message,
    ModelSpec,
    ProviderError,
    ProviderResult,
    StructuredOutputError,
)


@dataclass
class FakeCall:
    spec: ModelSpec
    messages: list[Message]
    response_model: type[BaseModel] | None


@dataclass
class FakeProvider:
    name: str = "fake"
    text: str = "fake answer"
    structured: dict[str, Any] = field(default_factory=dict)
    fail_structured_times: int = 0
    fail_times: int = 0
    tokens_in: int = 10
    tokens_out: int = 5
    latency_ms: int = 1
    calls: list[FakeCall] = field(default_factory=list)
    vectors_dim: int = 8

    async def complete(
        self,
        spec: ModelSpec,
        messages: list[Message],
        *,
        response_model: type[BaseModel] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        metadata: dict[str, Any] | None = None,
    ) -> ProviderResult:
        self.calls.append(FakeCall(spec, messages, response_model))
        if self.fail_times > 0:
            self.fail_times -= 1
            raise ProviderError("fake transport failure")
        parsed: BaseModel | None = None
        text = self.text
        if response_model is not None:
            if self.fail_structured_times > 0:
                self.fail_structured_times -= 1
                raise StructuredOutputError("fake invalid output", attempts=3)
            parsed = response_model.model_validate(self.structured)
            text = parsed.model_dump_json()
        return ProviderResult(
            text=text,
            parsed=parsed,
            tokens_in=self.tokens_in,
            tokens_out=self.tokens_out,
            latency_ms=self.latency_ms,
            model=spec.model,
            provider=self.name,
        )

    async def stream(
        self,
        spec: ModelSpec,
        messages: list[Message],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        for word in self.text.split(" "):
            yield word + " "

    async def embed(self, spec: ModelSpec, texts: list[str]) -> list[list[float]]:
        return [hash_vector(t, self.vectors_dim) for t in texts]


def hash_vector(text: str, dim: int) -> list[float]:
    """Deterministic pseudo-embedding: bag-of-words hashed into `dim` buckets, L2-normalised."""
    import math

    v = [0.0] * dim
    for tok in text.lower().split():
        v[hash(tok) % dim] += 1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]
