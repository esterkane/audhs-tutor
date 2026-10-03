"""Typed diagnostics never classify or export arbitrary error text."""

import json
from types import SimpleNamespace

import pytest
from instructor.core.exceptions import InstructorRetryException
from pydantic import ValidationError

from app.models_ai.provider import StructuredOutputError, structured_reason
from app.schemas.feedback import bound_feedback


def wrapped(error):
    return InstructorRetryException(
        "PRIVATE_WRAPPER",
        n_attempts=1,
        total_usage=None,
        failed_attempts=[SimpleNamespace(exception=error)],
    )


@pytest.mark.parametrize(
    "code, quotes, followup",
    [
        ("quote_not_literal", ["PRIVATE_UNKNOWN"], None),
        ("quote_duplicate", ["answer", "answer"], None),
        ("explicit_followup_forbidden", ["answer"], "PRIVATE_QUESTION"),
    ],
)
def test_typed_feedback_reasons(code, quotes, followup):
    schema = bound_feedback("answer", socratic=False)
    with pytest.raises(ValidationError) as caught:
        schema.model_validate(
            {
                "points": [
                    dict(learner_quote=q, finding="supported", explanation="Synthetic")
                    for q in quotes
                ],
                "next_step": "Continue",
                "followup_question": followup,
            }
        )
    assert structured_reason(caught.value) == code
    assert structured_reason(wrapped(wrapped(caught.value))) == code
    assert "PRIVATE" not in structured_reason(caught.value)


def test_json_schema_unknown_latest_and_cycle():
    try:
        json.loads("PRIVATE_NOT_JSON")
    except json.JSONDecodeError as error:
        invalid = error
    assert structured_reason(invalid) == "invalid_json"
    schema = bound_feedback("answer", socratic=False)
    with pytest.raises(ValidationError) as caught:
        schema.model_validate({})
    assert structured_reason(caught.value) == "schema_validation"
    latest = wrapped(RuntimeError("quote_not_literal PRIVATE"))
    latest.failed_attempts.insert(0, SimpleNamespace(exception=invalid))
    assert structured_reason(latest) == "unknown"
    loop = RuntimeError("quote_duplicate")
    loop.__cause__ = loop
    assert structured_reason(loop) == "unknown"
    outer = RuntimeError("PRIVATE")
    outer.__cause__ = invalid
    assert structured_reason(outer) == "invalid_json"
    assert StructuredOutputError("PRIVATE", 1, reason_code="PRIVATE").reason_code == "unknown"


@pytest.mark.parametrize("provider", ["ollama", "openai", "claude"])
def test_provider_adapters_carry_only_typed_reason(provider):
    from importlib import import_module

    adapter = import_module("app.models_ai." + provider)
    assert (
        adapter._structured_error(wrapped(RuntimeError("quote_not_literal"))).reason_code
        == "unknown"
    )
    error = json.JSONDecodeError("PRIVATE", "PRIVATE", 0)
    assert adapter._structured_error(wrapped(error)).reason_code == "invalid_json"


async def test_gateway_persists_reason_and_diagnostic_export_allowlists_it(db):
    from sqlalchemy import select

    from app.db.models import ModelCall
    from app.models_ai.budget import Budget
    from app.models_ai.fake import FakeProvider
    from app.models_ai.gateway import ModelGateway
    from app.models_ai.provider import Message, TaskClass
    from app.models_ai.registry import seed_defaults
    from app.models_ai.routing import Router

    class FailOnce(FakeProvider):
        async def complete(self, *args, **kwargs):
            if not getattr(self, "failed_once", False):
                self.failed_once = True
                raise StructuredOutputError(
                    "PRIVATE_FAILURE", 1, reason_code="quote_not_literal", tokens_in=12
                )
            return await super().complete(*args, **kwargs)

    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    provider = FailOnce(
        structured={
            "points": [
                {"learner_quote": "answer", "finding": "supported", "explanation": "Synthetic"}
            ],
            "next_step": "Continue",
            "followup_question": None,
        }
    )
    gateway = ModelGateway(db, Router(), {"ollama": provider}, Budget(0))
    await gateway.complete(
        TaskClass.CHAT,
        [Message(role="user", content="answer")],
        response_model=bound_feedback("answer", socratic=False),
    )
    repair_message = provider.calls[0].messages[-1]
    assert repair_message.role == "user"
    assert "current learner_answer" in repair_message.content
    assert "Do not correct the learner" in repair_message.content
    assert "PRIVATE_FAILURE" not in repair_message.content
    calls = list(await db.scalars(select(ModelCall).order_by(ModelCall.attempt)))
    assert len(calls) == 2
    assert calls[0].outcome == "invalid_output"
    assert calls[0].metadata_json["structured_reason_code"] == "quote_not_literal"
    assert calls[0].tokens_in == 12
    assert "structured_reason_code" not in calls[1].metadata_json

    diagnostic = load_diagnostic()
    exported = diagnostic.attempt_diagnostic(calls[0])
    assert exported["structured_reason_code"] == "quote_not_literal"
    assert "PRIVATE_FAILURE" not in json.dumps(exported)
    calls[0].metadata_json = {"structured_reason_code": "PRIVATE_INJECTED"}
    assert diagnostic.attempt_diagnostic(calls[0])["structured_reason_code"] == "unknown"


def load_diagnostic():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "scripts/eval_local_runtime.py"
    spec = importlib.util.spec_from_file_location("typed_diagnostic", path)
    assert spec and spec.loader
    diagnostic = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(diagnostic)
    return diagnostic
