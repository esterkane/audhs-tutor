"""OpenAI Chat Completions via LiteLLM and Instructor; gateway owns retries and spend.

Reasoning is disabled explicitly: the selected model's Chat Completions tool calling requires
it. No hidden transport retries, provider cache directives, or SDK-derived invoice claims.
"""

import time
from collections.abc import AsyncIterator
from contextlib import suppress
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
    StreamEvent,
    StreamUsage,
    StructuredOutputError,
    to_chat,
    usage_of,
)
from app.models_ai.routing import load_profiles

litellm.suppress_debug_info = True


def supported_model(model: str) -> bool:
    return any(
        r["runtime"] == "openai" and (r.get("file_or_tag") or r["repo_id"]) == model
        for r in load_profiles()["registry_defaults"]
    )


class OpenAIProvider:
    name = "openai"

    def __init__(self, api_key: str, timeout_s: float = 120.0) -> None:
        if not api_key:
            raise ProviderError("OPENAI_API_KEY is empty; OpenAIProvider unavailable")
        self.api_key = api_key
        self.timeout_s = timeout_s
        self._instructor = cast(
            instructor.AsyncInstructor,
            instructor.from_litellm(litellm.acompletion, mode=instructor.Mode.TOOLS),
        )

    def _model(self, spec: ModelSpec) -> str:
        return f"openai/{spec.model}"

    def _validate(
        self,
        spec: ModelSpec,
        messages: list[Message],
        response_model: type[BaseModel] | None = None,
    ) -> None:
        if not supported_model(spec.model):
            raise ProviderError("OpenAI model is not in the verified registry defaults")
        # Keep this adapter within the short-context price tier, even with UTF-8/token overhead.
        import json

        size = len(json.dumps(to_chat(messages), ensure_ascii=True).encode())
        if response_model is not None:
            size += len(json.dumps(response_model.model_json_schema()).encode())
        if size > 100_000:
            raise ProviderError("OpenAI prompt too large for this short-context adapter")
        if spec.price_in_per_mtok <= 0 or spec.price_out_per_mtok <= 0:
            raise ProviderError("OpenAI registry prices must be positive")

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
        self._validate(spec, messages, response_model)
        t0 = time.perf_counter()
        kwargs: dict[str, Any] = dict(
            model=self._model(spec),
            messages=to_chat(messages),
            api_key=self.api_key,
            max_completion_tokens=max_tokens,
            reasoning_effort="none",
            api_base="https://api.openai.com/v1",
            num_retries=0,
            store=False,
            temperature=temperature,
            timeout=self.timeout_s,
            metadata=metadata or {},
        )
        try:
            if response_model is not None:
                parsed, completion = await self._instructor.chat.completions.create_with_completion(
                    response_model=response_model, max_retries=1, **kwargs
                )
                text = parsed.model_dump_json()
            else:
                completion = await litellm.acompletion(**kwargs)
                parsed = None
                text = completion.choices[0].message.content or ""
        except InstructorRetryException as e:
            raise _structured_error(e) from e
        except Exception as e:
            raise ProviderError(
                f"OpenAI request failed ({type(e).__name__}); check key, model access and network"
            ) from e
        tin, tout, cached = usage_of(completion)
        return ProviderResult(
            text=text,
            parsed=parsed,
            tokens_in=tin,
            tokens_out=tout,
            cached_tokens=cached,
            latency_ms=int((time.perf_counter() - t0) * 1000),
            model=spec.model,
            provider=self.name,
            reported_cost_usd=None,
        )

    async def stream(
        self,
        spec: ModelSpec,
        messages: list[Message],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> AsyncIterator[StreamEvent]:
        self._validate(spec, messages)
        usage: Any | None = None
        response: Any | None = None
        try:
            response = await litellm.acompletion(
                model=self._model(spec),
                messages=to_chat(messages),
                api_key=self.api_key,
                max_completion_tokens=max_tokens,
                reasoning_effort="none",
                api_base="https://api.openai.com/v1",
                num_retries=0,
                store=False,
                temperature=temperature,
                stream=True,
                stream_options={"include_usage": True},
                timeout=self.timeout_s,
            )
            async for chunk in response:
                if getattr(chunk, "usage", None) is not None:
                    usage = chunk.usage  # the provider's final usage chunk
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            raise ProviderError(
                f"OpenAI stream failed ({type(e).__name__}); check key, model access and network"
            ) from e
        finally:
            close = getattr(response, "aclose", None)
            if close is not None:
                with suppress(Exception):
                    await close()
        if usage is not None:
            tin, tout, cached = usage_of(usage)
            if tin or tout:
                yield StreamUsage(tokens_in=tin, tokens_out=tout, cached_tokens=cached)


def _structured_error(e: InstructorRetryException) -> StructuredOutputError:
    """Keep what the failed attempt cost and said: the provider billed it, the gateway logs it."""
    tin, tout, cached = usage_of(getattr(e, "total_usage", None))
    last = getattr(e, "last_completion", None)
    text: str | None = None
    try:
        if last is not None and last.choices:
            msg = last.choices[0].message
            text = msg.content
            if not text and getattr(msg, "tool_calls", None):  # instructor TOOLS mode
                text = msg.tool_calls[0].function.arguments
    except (AttributeError, IndexError):
        text = None
    return StructuredOutputError(
        "OpenAI structured response did not validate",
        attempts=int(getattr(e, "n_attempts", 1) or 1),
        tokens_in=tin,
        tokens_out=tout,
        cached_tokens=cached,
        last_text=text,
    )
