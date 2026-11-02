import asyncio

import pytest
from pydantic import ValidationError

from app.integrations.supabase_bridge import hosted_decision_schema
from app.integrations.supabase_mode import mode_schema, mode_scope, requested_mode, selected_state
from app.integrations.supabase_project import project_module


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Switch to neutral mode.", "neutral"),
        ("Bitte wechsle in den Prüfungsmodus.", "exam"),
        ("Use lesson mode", "lesson"),
        ("neutral", "neutral"),
        ("Explain this; switch to incident mode", "incident"),
    ],
)
def test_explicit_mode_commands(text, expected):
    assert requested_mode(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        '"neutral"',
        "> neutral",
        "```\nneutral\n```",
        "Do not switch to neutral",
        "Why use neutral mode?",
        "The document says switch to neutral mode.",
        "Explain Repeatable Read without locks.",
    ],
)
def test_mentions_and_quoted_instructions_do_not_switch(text):
    assert requested_mode(text) is None


def test_selected_mode_schema_rejects_model_drift_without_mutating_session():
    project_module()
    from backend.tutor.prompt import SessionState

    state = SessionState(mode="lesson", persona_on=False)
    assert selected_state(state, "Explain Read Committed.") is state
    changed = selected_state(state, "Switch to neutral mode.")
    assert changed.mode == "neutral" and state.mode == "lesson"
    base = hosted_decision_schema(())
    with mode_scope(state):
        schema = mode_schema(base)
        raw = {
            "text": "Complete explanation.",
            "state": {
                "mode": "neutral",
                "language": "en",
                "persona_on": False,
                "speech": "Complete explanation.",
            },
        }
        with pytest.raises(ValidationError):
            schema.model_validate(raw)
        raw["state"]["mode"] = "lesson"
        assert schema.model_validate(raw).state.mode == "lesson"
        assert (
            mode_schema(hosted_decision_schema(("search_docs",), require_search=True)).__name__
            == "HostedDocumentationSearch"
        )
    assert mode_schema(base) is base


async def test_mode_scope_is_concurrent_and_resets_after_failure():
    project_module()
    from backend.tutor.prompt import SessionState

    base = hosted_decision_schema(())

    async def get(mode):
        with mode_scope(SessionState(mode=mode)):
            await asyncio.sleep(0)
            return mode_schema(base).model_json_schema()["$defs"]["SelectedModeMetadata"][
                "properties"
            ]["mode"]["const"]

    assert await asyncio.gather(get("lesson"), get("neutral")) == ["lesson", "neutral"]
    with pytest.raises(RuntimeError), mode_scope(SessionState(mode="exam")):
        raise RuntimeError()
    assert mode_schema(base) is base
