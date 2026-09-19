"""OllamaProvider: general local inference (chat + structured JSON) and embeddings."""

import time
from collections.abc import AsyncIterator
from typing import Any, cast

import httpx
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
    to_chat,
    usage_of,
)

litellm.suppress_debug_info = True


class OllamaProvider:
    name = "ollama"

    def __init__(self, host: str, timeout_s: float = 180.0) -> None:
        self.host = host.rstrip("/")
        self.timeout_s = timeout_s
        self._instructor = cast(
            instructor.AsyncInstructor,
            instructor.from_litellm(litellm.acompletion, mode=instructor.Mode.JSON),
        )

    def _model(self, spec: ModelSpec) -> str:
        return f"ollama_chat/{spec.model}"

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
            messages=to_chat(messages),
            api_base=self.host,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=self.timeout_s,
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
        except Exception as e:  # httpx / litellm transport errors
            raise ProviderError(f"ollama {spec.model}: {e}") from e
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
            reported_cost_usd=0.0,
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
                messages=to_chat(messages),
                api_base=self.host,
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
            raise ProviderError(f"ollama stream {spec.model}: {e}") from e

    async def embed(self, spec: ModelSpec, texts: list[str]) -> list[list[float]]:
        """Ollama's native /api/embed (batched); returns one vector per input."""
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
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
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
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
