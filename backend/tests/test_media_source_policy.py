"""Synthetic media only; mocked transports prevent all external network access."""

from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from app.knowledge.ingest.vision import OllamaImageReader
from app.models_ai.source_policy import SourcePolicyDenied
from app.voice.tts import KokoroClient, kokoro_reachable


@pytest.mark.parametrize(
    "host", ["https://remote.example", "http://localhost@remote.example", "http://localhost/proxy"]
)
async def test_speech_rejects_remote_endpoint_before_transport(host, monkeypatch):
    client = Mock(side_effect=AssertionError("must not create remote transport"))
    monkeypatch.setattr(httpx, "AsyncClient", client)
    with pytest.raises(SourcePolicyDenied):
        _ = [
            chunk
            async for chunk in KokoroClient(host).stream(
                "private course text", voice="af_heart", lang="en"
            )
        ]
    client.assert_not_called()


@pytest.mark.parametrize("host", ["https://remote.example", "http://localhost?proxy=remote"])
def test_image_rejects_remote_before_sending_bytes(host, monkeypatch):
    post = Mock(side_effect=AssertionError("must not send image"))
    client = Mock(side_effect=AssertionError("must not create remote transport"))
    monkeypatch.setattr(httpx, "post", post)
    monkeypatch.setattr(httpx, "Client", client)
    with pytest.raises(SourcePolicyDenied):
        OllamaImageReader(host, "vision", registry_id="local").read(b"private", mime="image/png")
    post.assert_not_called()
    client.assert_not_called()


async def test_remote_kokoro_readiness_does_not_claim_local(monkeypatch):
    get = AsyncMock(return_value=httpx.Response(200))
    monkeypatch.setattr(httpx.AsyncClient, "get", get)
    assert not await kokoro_reachable("https://remote.example")
    get.assert_not_called()


@pytest.mark.parametrize(
    "details",
    [
        {},
        {"model_info": {"size": 1}, "remote_host": "cloud"},
        {"model_info": {"size": 1}, "remote_model": "cloud"},
        {"model_info": "not weights"},
    ],
)
def test_image_metadata_must_prove_local_weights(details, monkeypatch):
    requests = []
    original = httpx.Client

    def respond(request):
        requests.append(request)
        assert request.url.path == "/api/show"
        assert request.content == b'{"model":"vision"}'
        return httpx.Response(200, json=details)

    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(respond))
    )
    with pytest.raises(SourcePolicyDenied):
        OllamaImageReader("http://localhost:11434", "vision", registry_id="local").read(
            b"private", mime="image/png"
        )
    assert len(requests) == 1


def test_local_image_preserves_payload_and_transport_configuration(monkeypatch):
    import base64
    import json

    original = httpx.Client
    requests = []
    clients = []

    def respond(request):
        requests.append(request)
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"model_info": {"size": 1}})
        data = json.loads(request.content)
        assert base64.b64decode(data["images"][0]) == b"synthetic image"
        assert data["model"] == "vision"
        return httpx.Response(
            200, json={"response": "visible text", "prompt_eval_count": 4, "eval_count": 3}
        )

    def make_client(**kwargs):
        assert kwargs["trust_env"] is False and kwargs["follow_redirects"] is False
        client = original(**kwargs, transport=httpx.MockTransport(respond))
        clients.append(client)
        return client

    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.2:9999")
    monkeypatch.setattr(httpx, "Client", make_client)
    result = OllamaImageReader("http://localhost:11434", "vision", registry_id="local").read(
        b"synthetic image", mime="image/png"
    )
    assert (result.text, result.tokens_in, result.tokens_out) == ("visible text", 4, 3)
    assert [r.url.path for r in requests] == ["/api/show", "/api/generate"]
    assert clients[0].is_closed


@pytest.mark.parametrize("redirect", [False, True])
async def test_local_speech_transport_preserves_audio_and_does_not_follow_redirects(
    monkeypatch, redirect
):
    import json

    original = httpx.AsyncClient
    requests = []
    clients = []

    def respond(request):
        requests.append(request)
        assert request.url.host == "localhost"
        assert json.loads(request.content)["input"] == "synthetic explanation"
        if redirect:
            return httpx.Response(307, headers={"location": "https://remote.example/speech"})
        return httpx.Response(200, content=b"\x01\x00" * 120)

    def make_client(**kwargs):
        assert kwargs["trust_env"] is False and kwargs["follow_redirects"] is False
        client = original(**kwargs, transport=httpx.MockTransport(respond))
        clients.append(client)
        return client

    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.2:9999")
    monkeypatch.setattr(httpx, "AsyncClient", make_client)

    async def consume():
        return [
            c
            async for c in KokoroClient("http://localhost:8880").stream(
                "synthetic explanation", voice="af_heart", lang="en"
            )
        ]

    if redirect:
        with pytest.raises(httpx.HTTPStatusError):
            await consume()
    else:
        chunks = await consume()
        assert b"".join(c.pcm16 for c in chunks) == b"\x01\x00" * 120
        assert all(c.sample_rate == 24000 for c in chunks)
    assert len(requests) == 1
    assert clients[0].is_closed


@pytest.mark.parametrize(
    "payload, expected",
    [
        (
            {
                "voices": [
                    {"id": "af_heart", "name": "Friendly voice"},
                    "af_bella",
                    {"name": "No ID"},
                    None,
                ]
            },
            ["af_heart", "af_bella"],
        ),
        (["af_heart"], ["af_heart"]),
        ({"voices": "not a list"}, []),
    ],
)
async def test_voice_listing_returns_usable_ids(payload, expected, monkeypatch):
    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original(
            **kwargs,
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload)),
        ),
    )
    assert await KokoroClient("http://localhost:8880").voices() == expected
