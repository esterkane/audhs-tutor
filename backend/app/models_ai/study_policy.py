"""Exact-message hosted study permits issued by owner-enabled server orchestration."""

import hashlib
import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from app.models_ai.provider import HOSTED_PROVIDERS, Message, ModelSpec
from app.models_ai.source_policy import SourcePolicyDenied


@dataclass(frozen=True)
class StudyPermit:
    registry_id: str
    provider: str
    message_json: str
    expires: float


_study: ContextVar[StudyPermit | None] = ContextVar("hosted_study", default=None)


def study_scope_active() -> bool:
    return _study.get() is not None


def study_transport_allowed(spec: ModelSpec) -> bool:
    permit = _study.get()
    return bool(
        permit
        and spec.registry_id == permit.registry_id
        and spec.provider == permit.provider
        and permit.expires >= time.monotonic()
    )


@contextmanager
def study_scope(spec: ModelSpec, messages: list[Message]) -> Iterator[str]:
    """Called only after server preference, model, credential and budget checks."""
    if spec.provider not in HOSTED_PROVIDERS or _study.get() is not None:
        raise SourcePolicyDenied("Invalid hosted study scope")
    serialized = json.dumps([message.model_dump() for message in messages], sort_keys=True)
    token = _study.set(
        StudyPermit(spec.registry_id, spec.provider, serialized, time.monotonic() + 600)
    )
    try:
        yield hashlib.sha256(serialized.encode()).hexdigest()
    finally:
        _study.reset(token)


def check_study_messages(spec: ModelSpec, messages: list[Message]) -> None:
    permit = _study.get()
    if not study_transport_allowed(spec) or permit is None:
        raise SourcePolicyDenied("No current study permission for this model")
    if [message.model_dump() for message in messages] != json.loads(permit.message_json):
        raise SourcePolicyDenied("Study content changed after permission was issued")


def bind_study_repair(spec: ModelSpec, messages: list[Message]) -> None:
    permit = _study.get()
    if permit is None:
        return
    original = json.loads(permit.message_json)
    check_study_messages(spec, messages[: len(original)])
    extra = messages[len(original) :]
    if (
        len(extra) not in (1, 2)
        or extra[-1].role != "user"
        or not extra[-1].content.startswith(
            "Your previous reply did not match the required JSON schema:"
        )
        or (len(extra) == 2 and (extra[0].role != "assistant" or len(extra[0].content) > 4000))
    ):
        raise SourcePolicyDenied("Unbound hosted study repair")
    _study.set(
        StudyPermit(
            permit.registry_id,
            permit.provider,
            json.dumps([message.model_dump() for message in messages], sort_keys=True),
            permit.expires,
        )
    )


def permitted_study_bytes(spec: ModelSpec) -> int:
    # Model context includes output/schema overhead; retain a conservative byte bound.
    return (
        900000 if study_transport_allowed(spec) and (spec.context_len or 0) >= 1000000 else 100000
    )
