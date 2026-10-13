"""The vector index cannot silently export corpus/query data via URL, proxy or redirect."""

import httpx
import pytest

from app.knowledge import qdrant_transport, reindex
from app.models_ai.source_policy import SourcePolicyDenied


@pytest.mark.parametrize(
    "url", ["https://example.com", "http://user@localhost:6333", "http://localhost:6333/proxy"]
)
def test_remote_corpus_transport_refused_before_client(url, monkeypatch):
    def forbidden(**kwargs):
        pytest.fail("client must not be constructed")

    monkeypatch.setattr(qdrant_transport, "AsyncQdrantClient", forbidden)
    with pytest.raises(SourcePolicyDenied):
        qdrant_transport.local_qdrant_client(url)


async def test_invalid_index_endpoint_refused_before_embedding(db, monkeypatch):
    from app.core.config import Settings

    async def forbidden(*args, **kwargs):
        pytest.fail("model lookup must not happen")

    monkeypatch.setattr(reindex, "embed_spec", forbidden)
    with pytest.raises(SourcePolicyDenied):
        await reindex.build_repo(db, Settings(qdrant_url="https://example.com"))


async def test_real_sdk_rest_transport_is_local_and_does_not_follow_redirects(monkeypatch):
    import qdrant_client.async_qdrant_remote as remote
    from qdrant_client.http import api_client
    from qdrant_client.http.exceptions import UnexpectedResponse

    seen = []
    options = {}
    original = httpx.AsyncClient

    def respond(request):
        seen.append(str(request.url))
        return httpx.Response(
            307, headers={"location": "https://example.com/corpus"}, content=b"redirect"
        )

    def client(**kwargs):
        options.update(kwargs)
        return original(**kwargs, transport=httpx.MockTransport(respond))

    def forbid_thread(*args, **kwargs):
        pytest.fail("alternate compatibility transport must not start")

    monkeypatch.setattr(remote, "Thread", forbid_thread)
    monkeypatch.setenv("HTTP_PROXY", "http://example.com:8080")
    monkeypatch.setattr(api_client, "AsyncClient", client)
    index = qdrant_transport.local_qdrant_client("http://127.0.0.1:6333")
    try:
        with pytest.raises(UnexpectedResponse):
            await index.get_collections()
    finally:
        await index.close()
    assert options["trust_env"] is False and options["follow_redirects"] is False
    assert seen == ["http://127.0.0.1:6333/collections"]
