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
    StreamEvent,
    StreamUsage,
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
    stream_usage: tuple[int, int] | None = None  # (tokens_in, tokens_out) final usage chunk
    reported_cost_usd: float | None = None
    stream_delay_s: float = 0.0  # await between words (lets a test cancel mid-stream)
    fail_after_words: int | None = None  # break the stream after n words (partial)

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
        self.calls.append(FakeCall(spec, messages, response_model))
        if self.fail_times > 0:
            self.fail_times -= 1
            raise ProviderError("fake transport failure")
        parsed: BaseModel | None = None
        text = self.text
        if response_model is not None:
            if self.fail_structured_times > 0:
                self.fail_structured_times -= 1
                raise StructuredOutputError(
                    "fake invalid output",
                    attempts=1,
                    tokens_in=self.tokens_in,
                    tokens_out=self.tokens_out,
                    last_text="{not json",
                )
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
            reported_cost_usd=self.reported_cost_usd,
        )

    async def stream(
        self,
        spec: ModelSpec,
        messages: list[Message],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> AsyncIterator[StreamEvent]:
        self.calls.append(FakeCall(spec, messages, None))
        if self.fail_times > 0:
            self.fail_times -= 1
            raise ProviderError("fake transport failure")
        words = self.text.split(" ")
        for i, word in enumerate(words):
            if self.fail_after_words is not None and i >= self.fail_after_words:
                raise ProviderError("fake stream broke mid-way")
            if self.stream_delay_s:
                import asyncio

                await asyncio.sleep(self.stream_delay_s)
            yield word + (" " if i < len(words) - 1 else "")
        if self.stream_usage is not None:
            yield StreamUsage(tokens_in=self.stream_usage[0], tokens_out=self.stream_usage[1])

    async def embed(self, spec: ModelSpec, texts: list[str]) -> list[list[float]]:
        return [hash_vector(t, self.vectors_dim) for t in texts]


def hash_vector(text: str, dim: int) -> list[float]:
    """Deterministic pseudo-embedding: bag-of-words hashed into `dim` buckets, L2-normalised.
    Uses crc32, not `hash()` — Python's str hash is salted per process and made retrieval tests
    flaky across runs."""
    import math
    import zlib

    v = [0.0] * dim
    for tok in text.lower().split():
        v[zlib.crc32(tok.encode()) % dim] += 1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]
