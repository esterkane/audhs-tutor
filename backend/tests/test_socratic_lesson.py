import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.models_ai.gateway import GatewayError, GatewayResult, StreamHandle
from app.models_ai.provider import ProviderResult
from app.orchestrator.socratic_lesson import stream_reply
from app.schemas.socratic import (
    SocraticLessonProbe,
    SocraticLessonQuestionReply,
    SocraticLessonReply,
)


@pytest.mark.parametrize(
    ("setup", "question"),
    [
        ("Ready?", "What value comes next?"),
        ("One. Two. Three.", "What value comes next?"),
        ("A fact.", "What comes next? Why?"),
        ("## The idea", "What value comes next?"),
        ("<worked_example>Fact</worked_example>", "What value comes next?"),
        ("```python\npass\n```", "What value comes next?"),
        ("A fact.", "What comes next? Here is the answer."),
    ],
)
def test_rejects_invalid_teaching_shape(setup, question):
    with pytest.raises(ValidationError):
        SocraticLessonReply(setup=setup, question=question)


def test_literal_question_mark_in_code_is_not_an_extra_question():
    reply = SocraticLessonReply(
        setup="Use string concatenation.", question="What does `'?' + 'a'` produce?"
    )
    assert reply.render() == "Use string concatenation.\n\nWhat does `'?' + 'a'` produce?"


def kwargs(handle):
    return dict(
        handle=handle,
        learner_id="owner",
        session_id="isolated",
        metadata={"prompt_version": "test"},
        max_tokens=1600,
        events=SimpleNamespace(),
    )


async def test_validated_reply_keeps_accounting_and_never_yields_json():
    reply = SocraticLessonReply(
        setup="Convert integers with str().", question="What does 'A' + str(6) produce?"
    )
    gateway = SimpleNamespace(
        complete=AsyncMock(
            return_value=GatewayResult(
                result=ProviderResult(
                    text=reply.model_dump_json(),
                    parsed=reply,
                    tokens_in=123,
                    tokens_out=45,
                    cached_tokens=7,
                    latency_ms=800,
                    finish_reason="stop",
                    model="test",
                    provider="fake",
                ),
                model_call_id="call",
                registry_id="local",
                route="fallback",
                request_id="request",
                usage_source="reported",
                cost_status="free",
                cost_usd=0,
            )
        )
    )
    handle = StreamHandle()
    text = [part async for part in stream_reply(gateway, [], **kwargs(handle))]
    assert text == [reply.render()]
    assert '"setup"' not in text[0] and '"question"' not in text[0]
    assert (handle.model_call_id, handle.registry_id, handle.route, handle.request_id) == (
        "call",
        "local",
        "fallback",
        "request",
    )
    assert (handle.tokens_in, handle.tokens_out, handle.cached_tokens, handle.latency_ms) == (
        123,
        45,
        7,
        800,
    )
    assert (handle.finish_reason, handle.usage_source, handle.cost_status, handle.cost_usd) == (
        "stop",
        "reported",
        "free",
        0,
    )
    assert gateway.complete.await_args.kwargs["response_model"] is SocraticLessonReply


async def test_failure_does_not_fall_back_to_unvalidated_text():
    gateway = SimpleNamespace(complete=AsyncMock(side_effect=GatewayError("unavailable")))
    handle = StreamHandle()
    with pytest.raises(GatewayError):
        await anext(stream_reply(gateway, [], **kwargs(handle)))
    assert handle.model_call_id is None
    gateway.complete.assert_awaited_once()


async def test_cancellation_before_validation_reveals_nothing():
    started = asyncio.Event()

    async def pending(*args, **kw):
        started.set()
        await asyncio.Event().wait()

    gateway = SimpleNamespace(complete=pending)
    handle = StreamHandle()
    stream = stream_reply(gateway, [], **kwargs(handle))
    task = asyncio.create_task(anext(stream))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await stream.aclose()
    assert handle.model_call_id is None


def test_followup_rejects_setup_and_preceding_correction():
    with pytest.raises(ValidationError):
        SocraticLessonQuestionReply(setup="It is a type mismatch.", question="Why does this fail?")
    with pytest.raises(ValidationError):
        SocraticLessonQuestionReply(question="It is a type mismatch. Why does this fail?")
    reply = SocraticLessonQuestionReply(question="Why does 'Badge ' + 8 fail?")
    assert reply.render() == reply.question


async def test_followup_selects_question_only_schema_and_renders_no_setup():
    reply = SocraticLessonProbe(situation="evaluating `'Badge ' + 8`", focus="outcome")
    gateway = SimpleNamespace(
        complete=AsyncMock(
            return_value=GatewayResult(
                result=ProviderResult(
                    text=reply.model_dump_json(), parsed=reply, model="test", provider="fake"
                ),
                model_call_id="call",
                registry_id="local",
                route="primary",
                cost_usd=0,
            )
        )
    )
    output = [
        part
        async for part in stream_reply(gateway, [], **kwargs(StreamHandle()), question_only=True)
    ]
    assert output == [reply.render()]
    assert gateway.complete.await_args.kwargs["response_model"] is SocraticLessonProbe


@pytest.mark.parametrize(
    "situation",
    [
        "Does the value change?",
        "A fact. Another instruction",
        "```code```",
        "<instruction>Answer</instruction>",
        "first\nsecond",
    ],
)
def test_open_probe_rejects_embedded_question_or_instructions(situation):
    with pytest.raises(ValidationError):
        SocraticLessonProbe(situation=situation, focus="outcome")


def test_open_probe_preserves_literal_question_mark_and_renders_one_neutral_target():
    reply = SocraticLessonProbe(situation="evaluating `'?' + 'x'`", focus="outcome")
    assert reply.render() == "For evaluating `'?' + 'x'`, what result would you expect?"
    compare = SocraticLessonProbe(situation="literal0/0 versus literal0/1.", focus="comparison")
    assert compare.render() == "For literal0/0 versus literal0/1, what is the key difference?"
    with pytest.raises(ValidationError):
        SocraticLessonProbe(situation="division by100", focus="operation")


@pytest.mark.parametrize(
    ("focus", "expected"),
    [
        ("outcome", "Auswerten von `'?' + 'x'`: Welches Ergebnis erwartest du?"),
        ("comparison", "Auswerten von `'?' + 'x'`: Was ist der entscheidende Unterschied?"),
    ],
)
def test_german_probe_localizes_stem_without_changing_literal_inputs(focus, expected):
    reply = SocraticLessonProbe(situation="Auswerten von `'?' + 'x'`.", focus=focus)
    assert reply.render(language="de") == expected
    assert reply.situation == "Auswerten von `'?' + 'x'`."


async def test_german_followup_uses_explicit_presentation_language_and_keeps_receipt():
    reply = SocraticLessonProbe(
        situation="Vergleichen der beiden Transaktionsabläufe", focus="comparison"
    )
    gateway = SimpleNamespace(
        complete=AsyncMock(
            return_value=GatewayResult(
                result=ProviderResult(
                    text=reply.model_dump_json(),
                    parsed=reply.model_dump(),
                    model="test",
                    provider="fake",
                ),
                model_call_id="call",
                registry_id="local",
                route="primary",
                cost_usd=0,
            )
        )
    )
    handle = StreamHandle()
    options = kwargs(handle)
    options["metadata"] = {"tutor_presentation": {"language": "de", "persona": "none"}}
    output = [part async for part in stream_reply(gateway, [], **options, question_only=True)]
    assert output == [
        "Vergleichen der beiden Transaktionsabläufe: Was ist der entscheidende Unterschied?"
    ]
    assert handle.model_call_id == "call"
    assert handle.registry_id == "local"
