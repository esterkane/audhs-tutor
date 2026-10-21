"""OllamaProvider: general local inference (chat + structured JSON) and embeddings."""

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast
from urllib.parse import urlparse

import httpx
import instructor
import litellm
from instructor.core.exceptions import InstructorRetryException
from litellm.llms.custom_httpx.http_handler import AsyncHTTPHandler
from pydantic import BaseModel

from app.models_ai.context_capacity import context_capacity
from app.models_ai.provider import (
    InferenceTiming,
    Message,
    ModelSpec,
    ProviderError,
    ProviderResult,
    StreamEvent,
    StreamFinish,
    StreamUsage,
    StructuredOutputError,
    structured_reason,
    to_chat,
    usage_of,
)
from app.models_ai.source_policy import SourcePolicyDenied, require_local_weights, require_loopback

litellm.suppress_debug_info = True


@asynccontextmanager
async def _local_sdk_client(
    timeout_s: float, timings: list[InferenceTiming] | None = None
) -> AsyncIterator[AsyncHTTPHandler]:
    """Pin LiteLLM/Instructor to the same no-proxy/no-redirect transport as native calls."""
    handler = AsyncHTTPHandler(timeout=timeout_s)
    await handler.client.aclose()

    async def observe(response: httpx.Response) -> None:
        if timings is None or response.request.url.path != "/api/chat" or not response.is_success:
            return
        try:
            # This opt-in path is buffered native-schema completion, never streaming.
            # Reading the body here preserves it for the SDK's normal parsing.
            await response.aread()
            payload = response.json()
            keys = [
                "load_duration",
                "prompt_eval_duration",
                "eval_duration",
                "total_duration",
                "prompt_eval_count",
                "eval_count",
            ]
            values = [payload.get(key) for key in keys]
            if not all(type(value) is int and value >= 0 for value in values):
                return
            timings.append(
                InferenceTiming(
                    load_ms=values[0] / 1e6,
                    prompt_ms=values[1] / 1e6,
                    generation_ms=values[2] / 1e6,
                    total_ms=values[3] / 1e6,
                    prompt_tokens=values[4],
                    generated_tokens=values[5],
                )
            )
        except Exception:
            # Missing/changed diagnostics must never change answer handling.
            pass

    async with httpx.AsyncClient(
        timeout=timeout_s,
        trust_env=False,
        follow_redirects=False,
        event_hooks={"response": [observe]} if timings is not None else {},
    ) as client:
        handler.client = client
        yield handler


class OllamaProvider:
    name = "ollama"

    def __init__(
        self,
        host: str,
        timeout_s: float = 180.0,
        *,
        keep_alive_s: int = 1800,
        context_tokens: int = 16384,
        context_tokenizers: dict[str, str] | None = None,
    ) -> None:
        self.host = host.rstrip("/")
        self.timeout_s = timeout_s
        self.keep_alive_s = keep_alive_s
        self.context_tokens = context_tokens
        self.context_tokenizers = dict(context_tokenizers or {})
        self._instructor = cast(
            instructor.AsyncInstructor,
            instructor.from_litellm(litellm.acompletion, mode=instructor.Mode.JSON),
        )

    def _context_tokens(self, spec: ModelSpec, messages: list[Message], max_tokens: int) -> int:
        return context_capacity(
            min(self.context_tokens, spec.context_len or self.context_tokens),
            messages,
            max_tokens,
            self.context_tokenizers.get(spec.registry_id),
        )

    def _structured_context_tokens(
        self,
        spec: ModelSpec,
        messages: list[Message],
        max_tokens: int,
        response_model: type[BaseModel],
    ) -> int:
        ceiling = min(self.context_tokens, spec.context_len or self.context_tokens)
        if not self.context_tokenizers.get(spec.registry_id):
            return ceiling
        try:
            # Use the installed Instructor JSON transformation, including its schema
            # and system-message expansion. Recompute on every gateway repair: the
            # rejected response and validation messages must count too. No truncation.
            from instructor.v2.core.response import handle_response_model

            _, prepared = handle_response_model(
                response_model, mode=instructor.Mode.JSON, messages=to_chat(messages)
            )
            expanded = [Message(**message) for message in prepared["messages"]]
            return self._context_tokens(spec, expanded, max_tokens)
        except Exception:
            # Version changes or unsupported message shapes retain the full capacity.
            return ceiling

    def _model(self, spec: ModelSpec) -> str:
        return f"ollama_chat/{spec.model}"

    async def validate_local_transport(self, spec: ModelSpec) -> None:
        """Inspect local model metadata without sending learner content."""
        require_loopback(self.host)
        try:
            async with httpx.AsyncClient(
                timeout=min(self.timeout_s, 10.0), trust_env=False, follow_redirects=False
            ) as client:
                response = await client.post(f"{self.host}/api/show", json={"model": spec.model})
                response.raise_for_status()
                details = response.json()
            require_local_weights(details)
        except (httpx.HTTPError, ValueError) as exc:
            raise SourcePolicyDenied("Source policy: cannot verify local model transport") from exc

    async def is_resident(self, spec: ModelSpec) -> bool:
        """Check actual local residency; a recent preload can have been evicted."""
        require_loopback(self.host)
        if spec.provider != "ollama" or spec.hosted:
            return False
        async with httpx.AsyncClient(
            timeout=min(self.timeout_s, 3.0), trust_env=False, follow_redirects=False
        ) as client:
            response = await client.get(f"{self.host}/api/ps")
            response.raise_for_status()
            models = response.json().get("models", [])
        names = {spec.model, spec.model + ":latest"} if ":" not in spec.model else {spec.model}
        return any(
            isinstance(model, dict) and (model.get("name") in names or model.get("model") in names)
            for model in models
        )

    async def preload(self, spec: ModelSpec) -> bool:
        """Load an installed local model only; no prompts, inference or model pull."""
        if (
            urlparse(self.host).hostname not in {"localhost", "127.0.0.1", "::1"}
            or spec.provider != "ollama"
            or self.keep_alive_s == 0
        ):
            return False
        async with httpx.AsyncClient(timeout=min(self.timeout_s, 30.0)) as client:
            info = await client.post(f"{self.host}/api/show", json={"model": spec.model})
            info.raise_for_status()
            details = info.json()
            # Cloud aliases may still have provider=ollama. Require local weight metadata,
            # and inspect upstream metadata rather than trusting a model's display name.
            if (
                details.get("remote_host")
                or details.get("remote_model")
                or not details.get("model_info")
            ):
                return False
            response = await client.post(
                f"{self.host}/api/chat",
                json={
                    "model": spec.model,
                    "stream": False,
                    "keep_alive": self.keep_alive_s,
                    "options": {"num_ctx": self._context_tokens(spec, [], 1600)},
                },
            )
            response.raise_for_status()
            payload = response.json()
            if not payload.get("done") or payload.get("message", {}).get("content"):
                raise ProviderError("Local model preparation did not return an empty completion")
            return True

    async def _complete_schema(
        self,
        spec: ModelSpec,
        messages: list[Message],
        response_model: type[BaseModel],
        max_tokens: int,
        temperature: float,
        max_retries: int,
    ) -> ProviderResult:
        from instructor.v2.core.response import handle_response_model

        # Preserve the exact established JSON-mode instructions, not merely the data.
        # The shorter schema-only variant failed paragraph completeness in evaluation.
        _, expanded = handle_response_model(
            response_model, mode=instructor.Mode.JSON, messages=to_chat(messages)
        )
        schema_client = cast(
            instructor.AsyncInstructor,
            instructor.from_litellm(litellm.acompletion, mode=instructor.Mode.JSON_SCHEMA),
        )
        timings: list[InferenceTiming] = []
        started = time.perf_counter()
        async with _local_sdk_client(self.timeout_s, timings) as transport:
            try:
                parsed, completion = await schema_client.chat.completions.create_with_completion(
                    response_model=response_model,
                    # Instructor v2 counts retries AFTER the first request.
                    # The gateway owns subsequent logged validation attempts.
                    max_retries=max(max_retries - 1, 0),
                    client=transport,
                    model=self._model(spec),
                    messages=expanded["messages"],
                    api_base=self.host,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=self.timeout_s,
                    keep_alive=self.keep_alive_s,
                    num_ctx=(
                        self._structured_context_tokens(spec, messages, max_tokens, response_model)
                        if max_retries <= 1
                        else min(self.context_tokens, spec.context_len or self.context_tokens)
                    ),
                )
            except InstructorRetryException as exc:
                raise _structured_error(exc) from exc
            except Exception as exc:
                raise ProviderError(f"ollama {spec.model}: {exc}") from exc
        tin, tout, cached = usage_of(completion)
        reason = getattr(completion.choices[0], "finish_reason", None)
        thinking = getattr(completion.choices[0].message, "reasoning_content", None)
        return ProviderResult(
            text=parsed.model_dump_json(),
            parsed=parsed,
            tokens_in=tin,
            tokens_out=tout,
            cached_tokens=cached,
            latency_ms=int((time.perf_counter() - started) * 1000),
            model=spec.model,
            provider=self.name,
            reported_cost_usd=0.0,
            finish_reason=reason if isinstance(reason, str) else None,
            raw={"structured_output": "native_schema", "reasoning_chars": len(thinking or "")},
            inference_timing=timings[-1] if timings else None,
        )

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
        await self.validate_local_transport(spec)
        if (
            response_model is not None
            and metadata
            and metadata.get("structured_output") == "native_schema"
        ):
            return await self._complete_schema(
                spec, messages, response_model, max_tokens, temperature, max_retries
            )
        async with _local_sdk_client(self.timeout_s) as transport:
            t0 = time.perf_counter()
            kwargs: dict[str, Any] = dict(
                client=transport,
                model=self._model(spec),
                messages=to_chat(messages),
                api_base=self.host,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=self.timeout_s,
                keep_alive=self.keep_alive_s,
                num_ctx=(
                    (
                        self._structured_context_tokens(spec, messages, max_tokens, response_model)
                        if max_retries <= 1
                        else min(self.context_tokens, spec.context_len or self.context_tokens)
                    )
                    if response_model is not None
                    else self._context_tokens(spec, messages, max_tokens)
                ),
            )
            try:
                if response_model is not None:
                    (
                        parsed,
                        completion,
                    ) = await self._instructor.chat.completions.create_with_completion(
                        response_model=response_model, max_retries=max(max_retries, 1), **kwargs
                    )
                    text = parsed.model_dump_json()
                else:
                    completion = await litellm.acompletion(**kwargs)
                    parsed = None
                    text = completion.choices[0].message.content or ""
            except InstructorRetryException as e:
                raise _structured_error(e) from e
            except Exception as e:  # httpx / litellm transport errors
                raise ProviderError(f"ollama {spec.model}: {e}") from e
            tin, tout, cached = usage_of(completion)
            reason = getattr(completion.choices[0], "finish_reason", None)
            return ProviderResult(
                text=text,
                parsed=parsed,
                tokens_in=tin,
                tokens_out=tout,
                cached_tokens=cached,
                latency_ms=int((time.perf_counter() - t0) * 1000),
                model=spec.model,
                provider=self.name,
                reported_cost_usd=0.0,
                finish_reason=reason if isinstance(reason, str) else None,
            )

    async def stream(
        self,
        spec: ModelSpec,
        messages: list[Message],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> AsyncIterator[StreamEvent]:
        await self.validate_local_transport(spec)
        async with _local_sdk_client(self.timeout_s) as transport:
            usage: Any | None = None
            finish_reason: str | None = None
            try:
                response = await litellm.acompletion(
                    client=transport,
                    model=self._model(spec),
                    messages=to_chat(messages),
                    api_base=self.host,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=True,
                    stream_options={"include_usage": True},
                    timeout=self.timeout_s,
                    keep_alive=self.keep_alive_s,
                    num_ctx=self._context_tokens(spec, messages, max_tokens),
                )
                async for chunk in response:
                    if getattr(chunk, "usage", None) is not None:
                        usage = chunk.usage  # the provider's final usage chunk
                    if not chunk.choices:
                        continue
                    reason = getattr(chunk.choices[0], "finish_reason", None)
                    if isinstance(reason, str):
                        finish_reason = reason
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta
            except Exception as e:
                raise ProviderError(f"ollama stream {spec.model}: {e}") from e
            if usage is not None:
                tin, tout, cached = usage_of(usage)
                if tin or tout:
                    yield StreamUsage(tokens_in=tin, tokens_out=tout, cached_tokens=cached)

            if finish_reason is not None:
                yield StreamFinish(reason=finish_reason)

    async def embed(self, spec: ModelSpec, texts: list[str]) -> list[list[float]]:
        """Ollama's native /api/embed (batched); returns one vector per input."""
        await self.validate_local_transport(spec)
        async with httpx.AsyncClient(
            timeout=self.timeout_s, trust_env=False, follow_redirects=False
        ) as client:
            try:
                r = await client.post(
                    f"{self.host}/api/embed", json={"model": spec.model, "input": texts}
                )
                r.raise_for_status()
            except httpx.HTTPError as e:
                raise ProviderError(f"ollama embed {spec.model}: {e}") from e
        data = r.json()
        vectors: list[list[float]] = data.get("embeddings", [])
        if len(vectors) != len(texts):
            raise ProviderError(
                f"ollama embed returned {len(vectors)} vectors for {len(texts)} inputs"
            )
        return vectors

    async def generate_stats(
        self, spec: ModelSpec, prompt: str, max_tokens: int = 256
    ) -> dict[str, float]:
        """Native /api/generate call returning Ollama's own eval counters (for benchmarks)."""
        await self.validate_local_transport(spec)
        async with httpx.AsyncClient(
            timeout=self.timeout_s, trust_env=False, follow_redirects=False
        ) as client:
            r = await client.post(
                f"{self.host}/api/generate",
                json={
                    "model": spec.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": max_tokens},
                },
            )
            r.raise_for_status()
        d = r.json()
        eval_count = float(d.get("eval_count", 0))
        eval_ns = float(d.get("eval_duration", 1)) or 1.0
        return {
            "tokens_out": eval_count,
            "tok_per_s": eval_count / (eval_ns / 1e9),
            "prompt_eval_ms": float(d.get("prompt_eval_duration", 0)) / 1e6,
            "total_ms": float(d.get("total_duration", 0)) / 1e6,
        }


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
        str(e),
        attempts=int(getattr(e, "n_attempts", 1) or 1),
        tokens_in=tin,
        tokens_out=tout,
        cached_tokens=cached,
        last_text=text,
        reason_code=structured_reason(e),
    )
