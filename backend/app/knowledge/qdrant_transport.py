"""Local-only corpus transport; no proxy, redirect or background alternate HTTP path."""

from qdrant_client import AsyncQdrantClient

from app.models_ai.source_policy import require_loopback


def local_qdrant_client(url: str, *, timeout: int = 5) -> AsyncQdrantClient:
    require_loopback(url)
    return AsyncQdrantClient(
        url=url,
        timeout=timeout,
        prefer_grpc=False,
        cloud_inference=False,
        trust_env=False,
        follow_redirects=False,
        # The SDK's compatibility thread uses its own HTTP client without these controls.
        check_compatibility=False,
    )
