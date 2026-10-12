"""Fail-closed containment until version-bound owner-origin receipts exist.

No caller flag, registry label, API key or budget can authorize external content.
Adapter validation describes the actual transport, not the claimed model provider.
"""

from urllib.parse import urlparse

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
