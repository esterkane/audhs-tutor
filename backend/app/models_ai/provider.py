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


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


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
        return self.provider == "anthropic"

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


class ProviderError(Exception):
    """Transport/model failure. The gateway logs it and moves down the fallback chain."""


class StructuredOutputError(ProviderError):
    """Instructor exhausted `max_retries`; the gateway emits `invalid_output` and escalates."""

    def __init__(self, message: str, attempts: int) -> None:
        super().__init__(message)
        self.attempts = attempts


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
    ) -> ProviderResult: ...

    def stream(
        self,
        spec: ModelSpec,
        messages: list[Message],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]: ...


class EmbeddingProvider(Protocol):
    name: str

    async def embed(self, spec: ModelSpec, texts: list[str]) -> list[list[float]]: ...


def to_chat(messages: list[Message]) -> list[dict[str, str]]:
    return [m.model_dump() for m in messages]


def usage_of(completion: Any) -> tuple[int, int, int]:
    """(tokens_in, tokens_out, cached_tokens) from a LiteLLM/OpenAI-shaped usage object."""
    usage = getattr(completion, "usage", None)
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
