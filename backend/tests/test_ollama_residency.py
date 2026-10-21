from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.models_ai.factory import build_providers
from app.models_ai.ollama import OllamaProvider
from app.models_ai.provider import Message, ModelSpec


@pytest.fixture(autouse=True)
def isolated_protocol_transport(monkeypatch):
    """These protocol tests mock inference; real policy is tested in test_source_policy."""
    monkeypatch.setattr(OllamaProvider, "validate_local_transport", AsyncMock())


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
    assert call.call_args.kwargs["num_ctx"] == 16384

    async def chunks():
        yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="First"))])
        yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=" second"))])

    call.return_value = chunks()
    assert [part async for part in provider.stream(spec, messages)] == ["First", " second"]
    assert call.call_args.kwargs["keep_alive"] == seconds
    assert call.call_args.kwargs["stream"] is True
    assert call.call_args.kwargs["num_ctx"] == 16384


def test_residency_is_configurable_and_bounded():
    settings = Settings(
        _env_file=None, ollama_keep_alive_s=300, anthropic_api_key="", openai_api_key=""
    )
    provider = build_providers(settings)["ollama"]
    assert isinstance(provider, OllamaProvider)
    assert provider.keep_alive_s == 300
    assert provider.context_tokens == 16384
    for value in [-1, 86401]:
        with pytest.raises(ValidationError):
            Settings(_env_file=None, ollama_keep_alive_s=value)


async def test_runtime_context_respects_model_registry_limit(monkeypatch):
    completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Answer"))]
    )
    call = AsyncMock(return_value=completion)
    monkeypatch.setattr("app.models_ai.ollama.litellm.acompletion", call)
    provider = OllamaProvider("http://localhost:11434", context_tokens=16384)
    await provider.complete(
        ModelSpec(registry_id="small", provider="ollama", model="small", context_len=8192),
        [Message(role="user", content="Explain")],
    )
    assert call.call_args.kwargs["num_ctx"] == 8192


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


async def test_capacity_applies_to_plain_stream_and_expanded_structured(monkeypatch):
    from pydantic import BaseModel

    class Answer(BaseModel):
        text: str

    provider = OllamaProvider(
        "http://localhost:11434", context_tokenizers={"local": "/matching.json"}
    )
    monkeypatch.setattr(
        "app.models_ai.ollama.context_capacity",
        lambda ceiling, messages, limit, path: 8192 if path else ceiling,
    )
    spec = ModelSpec(registry_id="local", provider="ollama", model="same-model")
    messages = [Message(role="user", content="Keep all of this content")]
    completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Answer"))]
    )
    call = AsyncMock(return_value=completion)
    monkeypatch.setattr("app.models_ai.ollama.litellm.acompletion", call)
    await provider.complete(spec, messages, max_tokens=1600)
    assert call.call_args.kwargs["num_ctx"] == 8192
    assert call.call_args.kwargs["max_tokens"] == 1600
    assert call.call_args.kwargs["messages"][0]["content"] == messages[0].content

    async def chunks():
        yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Answer"))])

    call.return_value = chunks()
    assert [part async for part in provider.stream(spec, messages, max_tokens=1600)] == ["Answer"]
    assert call.call_args.kwargs["num_ctx"] == 8192
    structured = AsyncMock(return_value=(Answer(text="Answer"), completion))
    provider._instructor = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create_with_completion=structured))
    )
    await provider.complete(spec, messages, response_model=Answer, max_tokens=1600)
    assert structured.call_args.kwargs["num_ctx"] == 8192
    await provider.complete(spec, messages, response_model=Answer, max_tokens=1600, max_retries=2)
    assert structured.call_args.kwargs["num_ctx"] == 16384
    assert (
        provider._context_tokens(
            ModelSpec(registry_id="other", provider="ollama", model="other"), messages, 1600
        )
        == 16384
    )


def test_structured_capacity_counts_exact_schema_and_each_repair(tmp_path, monkeypatch):
    import instructor
    from instructor.v2.core.response import handle_response_model
    from pydantic import BaseModel, Field

    from app.models_ai import context_capacity as capacity
    from app.models_ai.provider import to_chat

    class Answer(BaseModel):
        answer: str = Field(description="Evidence and complete answer")

    path = tmp_path / "matching.json"
    path.write_text("fixture")
    seen = []

    class Counter:
        def encode(self, text, add_special_tokens):
            seen.append(text)
            return SimpleNamespace(ids=list(range(len(text))))

    monkeypatch.setattr(capacity, "_load", lambda *args: Counter())
    provider = OllamaProvider("http://localhost:11434", context_tokenizers={"local": str(path)})
    spec = ModelSpec(registry_id="local", provider="ollama", model="same-model")
    messages = [
        Message(role="system", content="Stable policy"),
        Message(role="user", content="All original source text"),
    ]
    before = to_chat(messages)
    _, expanded = handle_response_model(
        Answer, mode=instructor.Mode.JSON, messages=to_chat(messages)
    )
    assert provider._structured_context_tokens(spec, messages, 1600, Answer) == 8192
    assert seen == [message["content"] for message in expanded["messages"]]
    assert "Evidence and complete answer" in " ".join(seen)
    assert to_chat(messages) == before
    # A long rejected response/validation repair expands the next call back to
    # full capacity. The entire requested output budget still counts.
    repair = messages + [
        Message(role="assistant", content="x" * 6500),
        Message(role="user", content="Repair the schema failure"),
    ]
    assert provider._structured_context_tokens(spec, repair, 1600, Answer) == 16384
    assert provider._structured_context_tokens(spec, messages, 12000, Answer) == 16384


def test_structured_capacity_fails_closed_for_schema_expansion(monkeypatch):
    from instructor.v2.core import response
    from pydantic import BaseModel

    class Answer(BaseModel):
        answer: str

    def unsupported(*args, **kwargs):
        raise ValueError("Changed Instructor protocol")

    monkeypatch.setattr(response, "handle_response_model", unsupported)
    provider = OllamaProvider(
        "http://localhost:11434", context_tokenizers={"local": "/matching.json"}
    )
    spec = ModelSpec(registry_id="local", provider="ollama", model="same-model")
    assert provider._structured_context_tokens(spec, [], 1600, Answer) == 16384
