"""Fail-closed study transport with an explicit, version-bound authoring exception.

Registry labels, keys, budgets and caller metadata alone never grant external transport.
Only server authoring orchestration issues a request-local exact-message permit (ADR 0021).
"""

import hashlib
import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from urllib.parse import urlparse

from app.models_ai.provider import Message, ModelSpec, ProviderError


@dataclass(frozen=True)
class AuthoringPermit:
    registry_id: str
    message_json: str
    expires: float


_authoring: ContextVar[AuthoringPermit | None] = ContextVar("hosted_authoring", default=None)


@contextmanager
def authoring_scope(registry_id: str, messages: list[Message]) -> Iterator[str]:
    """Server-issued, request-local permission; never activated by provider metadata."""
    serialized = json.dumps([m.model_dump() for m in messages], sort_keys=True)
    token = _authoring.set(AuthoringPermit(registry_id, serialized, time.monotonic() + 600))
    try:
        yield hashlib.sha256(serialized.encode()).hexdigest()
    finally:
        _authoring.reset(token)


def check_authoring_messages(spec: ModelSpec, messages: list[Message]) -> None:
    permit = _authoring.get()
    if (
        not permit
        or spec.provider != "openai"
        or permit.registry_id != spec.registry_id
        or permit.expires < time.monotonic()
    ):
        raise SourcePolicyDenied("No current authoring permission for this model")
    original = json.loads(permit.message_json)
    if [m.model_dump() for m in messages] != original:
        raise SourcePolicyDenied("Authoring content changed after permission was issued")


def bind_authoring_repair(spec: ModelSpec, messages: list[Message]) -> None:
    """Gateway-only extension with its bounded failed reply and structured repair instruction."""
    permit = _authoring.get()
    if permit is None:
        return  # ordinary local structured-output repair
    original = json.loads(permit.message_json)
    check_authoring_messages(spec, messages[: len(original)])
    extra = messages[len(original) :]
    if (
        len(extra) not in (1, 2)
        or extra[-1].role != "user"
        or not extra[-1].content.startswith(
            "Your previous reply did not match the required JSON schema:"
        )
        or (len(extra) == 2 and (extra[0].role != "assistant" or len(extra[0].content) > 4000))
    ):
        raise SourcePolicyDenied("Unbound authoring repair")
    _authoring.set(
        AuthoringPermit(
            permit.registry_id,
            json.dumps([m.model_dump() for m in messages], sort_keys=True),
            permit.expires,
        )
    )


class SourcePolicyDenied(ProviderError):
    """Content cannot be sent through this transport under the owner policy."""


async def validate_transport(
    provider: object, spec: ModelSpec, *, messages: list[Message] | None = None
) -> None:
    if spec.provider == "openai" and _authoring.get() is not None:
        check_authoring_messages(spec, messages or [])
    validate = getattr(provider, "validate_local_transport", None)
    if not callable(validate):
        raise SourcePolicyDenied("Source policy: provider transport is not verified local")
    await validate(spec)


async def deny_external(spec: ModelSpec) -> None:
    permit = _authoring.get()
    if (
        permit
        and spec.provider == "openai"
        and permit.registry_id == spec.registry_id
        and permit.expires >= time.monotonic()
    ):
        return
    raise SourcePolicyDenied(
        "Source policy: hosted inference is unavailable until complete owner-origin "
        "evidence is supported. Choose an installed local model."
    )


def require_loopback(endpoint_url: str) -> None:
    """Content-bearing services must be explicitly local, without a proxy path."""
    try:
        endpoint = urlparse(endpoint_url)
        valid = (
            endpoint.scheme in {"http", "https"}
            and endpoint.hostname in {"localhost", "127.0.0.1", "::1"}
            and endpoint.username is None
            and endpoint.password is None
            and endpoint.path in {"", "/"}
            and not endpoint.query
            and not endpoint.fragment
            and (endpoint.port is None or 0 < endpoint.port <= 65535)
        )
    except ValueError:
        valid = False
    if not valid:
        raise SourcePolicyDenied("Source policy: service endpoint must be local loopback")


def require_local_weights(details: object) -> None:
    if (
        not isinstance(details, dict)
        or details.get("remote_host")
        or details.get("remote_model")
        or not isinstance(details.get("model_info"), dict)
        or not details["model_info"]
    ):
        raise SourcePolicyDenied("Source policy: model local weights are unverified")
