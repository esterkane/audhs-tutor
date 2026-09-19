"""ClaudeProvider: hosted inference over the LiteLLM SDK (no proxy, ADR-0001).

Prompt caching: the first system message is marked `cache_control: ephemeral`; the orchestrator
guarantees that message is the byte-stable TutorPolicy (ARCHITECTURE §5).
"""

import time
from collections.abc import AsyncIterator
from typing import Any, cast

import instructor
import litellm
from instructor.core.exceptions import InstructorRetryException
from pydantic import BaseModel

from app.models_ai.provider import (
    Message,
    ModelSpec,
    ProviderError,
    ProviderResult,
    StructuredOutputError,
    usage_of,
)

litellm.suppress_debug_info = True


def _cached_chat(messages: list[Message]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    first_system = True
    for m in messages:
        if m.role == "system" and first_system:
            out.append(
                {
                    "role": "system",
                    "content": [
                        {"type": "text", "text": m.content, "cache_control": {"type": "ephemeral"}}
                    ],
                }
            )
            first_system = False
        else:
            out.append({"role": m.role, "content": m.content})
    return out


class ClaudeProvider:
    name = "anthropic"

    def __init__(self, api_key: str, timeout_s: float = 120.0) -> None:
        if not api_key:
            raise ProviderError("ANTHROPIC_API_KEY is empty; ClaudeProvider unavailable")
        self.api_key = api_key
        self.timeout_s = timeout_s
        self._instructor = cast(
            instructor.AsyncInstructor,
            instructor.from_litellm(litellm.acompletion, mode=instructor.Mode.TOOLS),
        )

    def _model(self, spec: ModelSpec) -> str:
        return f"anthropic/{spec.model}"

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
        t0 = time.perf_counter()
        kwargs: dict[str, Any] = dict(
            model=self._model(spec),
            messages=_cached_chat(messages),
            api_key=self.api_key,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=self.timeout_s,
            metadata=metadata or {},
        )
        try:
            if response_model is not None:
                parsed, completion = await self._instructor.chat.completions.create_with_completion(
                    response_model=response_model, max_retries=2, **kwargs
                )
                text = parsed.model_dump_json()
            else:
                completion = await litellm.acompletion(**kwargs)
                parsed = None
                text = completion.choices[0].message.content or ""
        except InstructorRetryException as e:
            raise StructuredOutputError(str(e), attempts=e.n_attempts) from e
        except Exception as e:
            raise ProviderError(f"anthropic {spec.model}: {e}") from e
        tin, tout, cached = usage_of(completion)
        reported: float | None
        try:
            reported = float(litellm.completion_cost(completion_response=completion))
        except Exception:
            reported = None
        return ProviderResult(
            text=text,
            parsed=parsed,
            tokens_in=tin,
            tokens_out=tout,
            cached_tokens=cached,
            latency_ms=int((time.perf_counter() - t0) * 1000),
            model=spec.model,
            provider=self.name,
            reported_cost_usd=reported,
        )

    async def stream(
        self,
        spec: ModelSpec,
        messages: list[Message],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        try:
            response = await litellm.acompletion(
                model=self._model(spec),
                messages=_cached_chat(messages),
                api_key=self.api_key,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                timeout=self.timeout_s,
            )
            async for chunk in response:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            raise ProviderError(f"anthropic stream {spec.model}: {e}") from e
