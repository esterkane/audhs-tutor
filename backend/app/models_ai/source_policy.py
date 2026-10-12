"""Fail-closed containment until version-bound owner-origin receipts exist.

No caller flag, registry label, API key or budget can authorize external content.
Adapter validation describes the actual transport, not the claimed model provider.
"""

from app.models_ai.provider import ModelSpec, ProviderError


class SourcePolicyDenied(ProviderError):
    """Content cannot be sent through this transport under the owner policy."""


async def validate_transport(provider: object, spec: ModelSpec) -> None:
    validate = getattr(provider, "validate_local_transport", None)
    if not callable(validate):
        raise SourcePolicyDenied("Source policy: provider transport is not verified local")
    await validate(spec)


async def deny_external(spec: ModelSpec) -> None:
    raise SourcePolicyDenied(
        "Source policy: hosted inference is unavailable until complete owner-origin "
        "evidence is supported. Choose an installed local model."
    )
