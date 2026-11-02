"""Structured Responses transport for explicitly selected project study models.

The gateway remains responsible for
request authorization, reservations, retries and persistence.
"""

import copy
import json
import time
from collections.abc import AsyncIterator
from typing import Any, Literal

from openai import AsyncOpenAI
from openai.lib._pydantic import to_strict_json_schema
from pydantic import BaseModel, ValidationError

from app.models_ai.openai import OpenAIProvider
from app.models_ai.provider import (
    Message,
    ModelSpec,
    ProviderError,
    ProviderResult,
    StreamEvent,
    StructuredOutputError,
    structured_reason,
)
from app.models_ai.source_policy import check_hosted_messages


def compatible_schema(schema: type[BaseModel]) -> dict[str, Any]:
    """Convert only provably disjoint tagged unions; keep local validation authoritative."""
    root = copy.deepcopy(to_strict_json_schema(schema))

    def visit(node: Any) -> None:
        if not isinstance(node, dict):
            return
        if node.get("type") == "object" and isinstance(node.get("additionalProperties"), dict):
            node.clear()
            node.update(
                type="string",
                description="JSON-encoded object. Preserve all keys and nested values.",
            )
            return
        if node.get("type") == "object" and node.get("additionalProperties") is True:
            node.clear()
            node.update(
                type="string",
                description="JSON-encoded object. Preserve all keys and nested values.",
            )
            return
        alternatives = node.get("anyOf")
        if alternatives is not None and not node.get("discriminator"):
            nonnull = [branch for branch in alternatives if branch.get("type") != "null"]
            if len(nonnull) > 1:
                # The inverse codec cannot select a branch unambiguously. Fail
                # before billing rather than rejecting every valid response later.
                raise ValueError("Unsupported untagged wire union")
        if "oneOf" in node:
            tag = node.get("discriminator", {}).get("propertyName")
            seen: set[str] = set()
            for branch in node["oneOf"]:
                resolved = branch
                if "$ref" in branch:
                    ref = branch["$ref"]
                    if not ref.startswith("#/$defs/"):
                        raise ValueError("Unsupported union reference")
                    resolved = root["$defs"][ref.removeprefix("#/$defs/")]
                value = resolved.get("properties", {}).get(tag, {}).get("const")
                if (
                    not isinstance(value, str)
                    or value in seen
                    or tag not in resolved.get("required", [])
                ):
                    raise ValueError("Cannot prove union alternatives are disjoint")
                seen.add(value)
            if not seen or "anyOf" in node:
                raise ValueError("Unsupported union shape")
            node["anyOf"] = node.pop("oneOf")
            node.pop("discriminator", None)
        # Defaults are annotations, not constraints; every wire field is required.
        node.pop("default", None)
        for key in ("properties", "$defs", "definitions"):
            for child in node.get(key, {}).values():
                visit(child)
        for key in ("items", "additionalProperties"):
            visit(node.get(key))
        for key in ("anyOf", "allOf", "oneOf"):
            for child in node.get(key, []):
                visit(child)

    visit(root)
    return root


def restore_objects(value: Any, schema: type[BaseModel]) -> Any:
    """Decode only schema-designated open objects, never arbitrary learner text."""
    root = to_strict_json_schema(schema)

    def restore(item: Any, node: dict[str, Any]) -> Any:
        if "$ref" in node:
            ref = node["$ref"]
            if not ref.startswith("#/$defs/"):
                raise ValueError("Unsupported object reference")
            return restore(item, root["$defs"][ref.removeprefix("#/$defs/")])
        branches = node.get("anyOf", node.get("oneOf"))
        if branches is not None:
            if item is None and any(b.get("type") == "null" for b in branches):
                return None
            tag = node.get("discriminator", {}).get("propertyName")
            candidates = []
            for branch in branches:
                resolved = (
                    root["$defs"][branch["$ref"].removeprefix("#/$defs/")]
                    if "$ref" in branch
                    else branch
                )
                if tag and isinstance(item, dict):
                    if resolved.get("properties", {}).get(tag, {}).get("const") == item.get(tag):
                        candidates.append(branch)
                elif resolved.get("type") != "null":
                    candidates.append(branch)
            if len(candidates) != 1:
                raise ValueError("Ambiguous wire object union")
            return restore(item, candidates[0])
        if node.get("type") == "object":
            additional = node.get("additionalProperties")
            if additional is True or isinstance(additional, dict):
                if not isinstance(item, str):
                    raise ValueError("Expected encoded object")
                decoded = json.loads(item)
                if not isinstance(decoded, dict):
                    raise ValueError("Encoded value must be an object")
                return decoded
            if isinstance(item, dict):
                return {
                    k: restore(v, node.get("properties", {}).get(k, {})) for k, v in item.items()
                }
        if node.get("type") == "array" and isinstance(item, list):
            return [restore(v, node.get("items", {})) for v in item]
        return item

    return restore(value, root)


def request_payload(
    model: str,
    messages: list[Message],
    schema: type[BaseModel],
    max_tokens: int,
    effort: Literal["low", "medium"],
) -> dict[str, Any]:
    if max_tokens <= 0 or effort not in {"low", "medium"}:
        raise ValueError("Invalid reasoning limits")
    return {
        "model": model,
        "input": [message.model_dump() for message in messages],
        "reasoning": {"effort": effort},
        "text": {
            "format": {
                "type": "json_schema",
                "name": schema.__name__,
                "schema": compatible_schema(schema),
                "strict": True,
            }
        },
        "max_output_tokens": max_tokens,
        "store": False,
        "service_tier": "default",
    }


def decode_response(
    response: Any,
    schema: type[BaseModel],
    model: str,
    latency_ms: int,
) -> ProviderResult:
    usage = getattr(response, "usage", None)
    tin = int(getattr(usage, "input_tokens", 0) or 0)
    tout = int(getattr(usage, "output_tokens", 0) or 0)
    details = getattr(usage, "input_tokens_details", None)
    cached = int(getattr(details, "cached_tokens", 0) or 0)
    text = getattr(response, "output_text", "") or ""
    refused = any(
        getattr(block, "type", None) == "refusal"
        for item in getattr(response, "output", [])
        for block in (getattr(item, "content", None) or [])
    )
    # output_tokens includes reasoning tokens. Never charge only visible text.
    if refused or getattr(response, "status", None) != "completed" or not text.strip():
        raise StructuredOutputError(
            "Responses output is incomplete or has no usable answer",
            1,
            tokens_in=tin,
            tokens_out=tout,
            cached_tokens=cached,
        )
    try:
        parsed = schema.model_validate(restore_objects(json.loads(text), schema))
    except (ValidationError, ValueError) as error:
        raise StructuredOutputError(
            "Responses output failed schema validation",
            1,
            tokens_in=tin,
            tokens_out=tout,
            cached_tokens=cached,
            last_text=text,
            reason_code=structured_reason(error),
        ) from error
    return ProviderResult(
        text=text,
        parsed=parsed,
        tokens_in=tin,
        tokens_out=tout,
        cached_tokens=cached,
        latency_ms=latency_ms,
        model=model,
        provider="openai",
        finish_reason="stop",
    )


class OpenAIResponsesProvider(OpenAIProvider):
    """Explicit reasoning transport; no silent changes to existing providers."""

    def __init__(
        self, api_key: str, *, effort: Literal["low", "medium"], timeout_s: float = 120.0
    ) -> None:
        super().__init__(api_key, timeout_s)
        if effort not in {"low", "medium"}:
            raise ValueError("Unsupported reasoning effort")
        self.effort = effort

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
        check_hosted_messages(spec, messages)
        self._validate(spec, messages, response_model)
        if response_model is None:
            raise ProviderError("Responses transport requires a structured answer contract")
        payload = request_payload(spec.model, messages, response_model, max_tokens, self.effort)
        started = time.perf_counter()
        try:
            async with AsyncOpenAI(
                api_key=self.api_key,
                base_url="https://api.openai.com/v1",
                max_retries=0,
                timeout=self.timeout_s,
            ) as client:
                response = await client.responses.create(**payload)
        except Exception as error:
            raise ProviderError(
                f"OpenAI Responses transport failed ({type(error).__name__})"
            ) from error
        return decode_response(
            response, response_model, spec.model, int((time.perf_counter() - started) * 1000)
        )

    async def stream(
        self,
        spec: ModelSpec,
        messages: list[Message],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> AsyncIterator[StreamEvent]:
        """Do not silently fall back to Chat Completions with different reasoning."""
        raise ProviderError("Responses transport supports structured complete only")
        yield  # pragma: no cover -- preserves the async iterator protocol
