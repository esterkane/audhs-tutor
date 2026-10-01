"""ModelProvider interface (ADR-0001). Model names never appear outside the registry/profiles.

Every call carries a `TaskClass`; the gateway resolves it to a registry entry (`ModelSpec`) and
writes a `model_call` row. Providers are thin adapters; they never decide routing or budget.
"""

from collections.abc import AsyncIterator
from enum import StrEnum
from typing import Any, Literal, Protocol, TypeVar

from pydantic import BaseModel, Field


class TaskClass(StrEnum):
    CHAT = "chat"
    CHAT_FAST = "chat_fast"
    FORMAT = "format"
    SUMMARIZE = "summarize"
    QUERY_EXPAND = "query_expand"
    GEN_ITEMS = "gen_items"
    EXPLAIN_SIMPLE = "explain_simple"
    HINT = "hint"
    CODE_LOCAL = "code_local"
    GRADE_SIMPLE = "grade_simple"
    GRADE_RUBRIC = "grade_rubric"
    TUTOR_DEEP = "tutor_deep"
    TUTOR_MEDIUM = "tutor_medium"
    SOCRATIC = "socratic"
    CHALLENGE = "challenge"
    CODE_REVIEW = "code_review"
    CONFLICT_RESOLUTION = "conflict_resolution"
    JUDGE = "judge"
    EMBED = "embed"
    RERANK = "rerank"
    STT = "stt"
    TTS = "tts"
    VISION = "vision"


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


HOSTED_PROVIDERS = ("anthropic", "openai")


class ModelSpec(BaseModel):
    """What a provider needs to make one call; built from a `model_registry` row."""

    registry_id: str
    provider: str  # ollama | anthropic | mlx | fake
    model: str  # runtime tag / hosted model id
    price_in_per_mtok: float = 0.0
    price_out_per_mtok: float = 0.0
    context_len: int | None = None

    @property
    def hosted(self) -> bool:
        return self.provider in HOSTED_PROVIDERS

    def cost(self, tokens_in: int, tokens_out: int) -> float:
        return round(
            tokens_in / 1e6 * self.price_in_per_mtok + tokens_out / 1e6 * self.price_out_per_mtok, 6
        )


class ProviderResult(BaseModel):
    text: str = ""
    parsed: Any | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    cached_tokens: int = 0
    latency_ms: int = 0
    first_token_ms: int | None = None
    model: str
    provider: str
    reported_cost_usd: float | None = None
    raw: dict[str, Any] = Field(default_factory=dict, exclude=True)


class StreamUsage(BaseModel):
    """Final usage of a stream when the provider sends one (P6). Yielded as the last item."""

    tokens_in: int = 0
    tokens_out: int = 0
    cached_tokens: int = 0
    reported_cost_usd: float | None = None


StreamEvent = str | StreamUsage


class ProviderError(Exception):
    """Transport/model failure. The gateway logs it and moves down the fallback chain."""


class StructuredOutputError(ProviderError):
    """The reply did not validate against the schema. Carries the attempt's usage (the provider
    billed it) and the invalid text so the gateway can log the attempt and ask for a repair."""

    def __init__(
        self,
        message: str,
        attempts: int,
        *,
        tokens_in: int = 0,
        tokens_out: int = 0,
        cached_tokens: int = 0,
        last_text: str | None = None,
    ) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.cached_tokens = cached_tokens
        self.last_text = last_text


T = TypeVar("T", bound=BaseModel)


class ModelProvider(Protocol):
    name: str

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
    ) -> ProviderResult: ...

    def stream(
        self,
        spec: ModelSpec,
        messages: list[Message],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> AsyncIterator[StreamEvent]: ...


class EmbeddingProvider(Protocol):
    name: str

    async def embed(self, spec: ModelSpec, texts: list[str]) -> list[list[float]]: ...


def to_chat(messages: list[Message]) -> list[dict[str, str]]:
    return [m.model_dump() for m in messages]


def usage_of(completion: Any) -> tuple[int, int, int]:
    """(tokens_in, tokens_out, cached_tokens) from a LiteLLM/OpenAI-shaped usage object (or the
    usage object itself)."""
    usage = getattr(completion, "usage", None)
    if usage is None and hasattr(completion, "prompt_tokens"):
        usage = completion
    if usage is None:
        return 0, 0, 0
    tin = int(getattr(usage, "prompt_tokens", 0) or 0)
    tout = int(getattr(usage, "completion_tokens", 0) or 0)
    cached = 0
    details = getattr(usage, "prompt_tokens_details", None)
    if details is not None:
        cached = int(getattr(details, "cached_tokens", 0) or 0)
    cached = cached or int(getattr(usage, "cache_read_input_tokens", 0) or 0)
    return tin, tout, cached
