from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.models_ai.factory import build_providers
from app.models_ai.ollama import OllamaProvider
from app.models_ai.provider import Message, ModelSpec


@pytest.mark.parametrize("seconds", [0, 300, 1800])
async def test_residency_reaches_complete_and_stream_without_changing_content(monkeypatch, seconds):
    provider = OllamaProvider("http://localhost:11434", keep_alive_s=seconds)
    spec = ModelSpec(registry_id="local", provider="ollama", model="same-model")
    messages = [Message(role="user", content="Same question and sources")]
    completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Answer"))]
    )
    call = AsyncMock(return_value=completion)
    monkeypatch.setattr("app.models_ai.ollama.litellm.acompletion", call)
    result = await provider.complete(spec, messages, max_tokens=120)
    assert result.text == "Answer"
    assert call.call_args.kwargs["keep_alive"] == seconds
    assert call.call_args.kwargs["messages"] == [{"role": "user", "content": messages[0].content}]
    assert call.call_args.kwargs["max_tokens"] == 120

    async def chunks():
        yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="First"))])
        yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=" second"))])

    call.return_value = chunks()
    assert [part async for part in provider.stream(spec, messages)] == ["First", " second"]
    assert call.call_args.kwargs["keep_alive"] == seconds
    assert call.call_args.kwargs["stream"] is True


def test_residency_is_configurable_and_bounded():
    settings = Settings(
        _env_file=None, ollama_keep_alive_s=300, anthropic_api_key="", openai_api_key=""
    )
    provider = build_providers(settings)["ollama"]
    assert isinstance(provider, OllamaProvider)
    assert provider.keep_alive_s == 300
    for value in [-1, 86401]:
        with pytest.raises(ValidationError):
            Settings(_env_file=None, ollama_keep_alive_s=value)


@pytest.mark.parametrize("reason", ["stop", "length"])
async def test_stream_keeps_finish_reason_separate_from_missing_usage(monkeypatch, reason):
    from app.models_ai.provider import StreamFinish

    async def chunks():
        yield SimpleNamespace(
            choices=[
                SimpleNamespace(delta=SimpleNamespace(content="unfinished"), finish_reason=None)
            ]
        )
        yield SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content=None), finish_reason=reason)]
        )

    monkeypatch.setattr(
        "app.models_ai.ollama.litellm.acompletion", AsyncMock(return_value=chunks())
    )
    provider = OllamaProvider("http://localhost:11434")
    parts = [
        part
        async for part in provider.stream(
            ModelSpec(registry_id="local", provider="ollama", model="test"),
            [Message(role="user", content="Explain")],
        )
    ]
    assert parts == ["unfinished", StreamFinish(reason=reason)]


@pytest.mark.parametrize("reason", [None, "stop", "length"])
async def test_buffered_completion_retains_finish_reason(monkeypatch, reason):
    completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Answer"), finish_reason=reason)],
        usage=SimpleNamespace(prompt_tokens=12, completion_tokens=4),
    )
    monkeypatch.setattr(
        "app.models_ai.ollama.litellm.acompletion", AsyncMock(return_value=completion)
    )
    result = await OllamaProvider("http://localhost:11434").complete(
        ModelSpec(registry_id="local", provider="ollama", model="test"),
        [Message(role="user", content="Explain")],
    )
    assert result.finish_reason == reason
    assert result.text == "Answer"
    assert (result.tokens_in, result.tokens_out) == (12, 4)
