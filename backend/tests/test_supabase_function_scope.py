from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.integrations.supabase_function_lookup import function_answer
from app.integrations.supabase_project import project_module


@pytest.mark.parametrize(
    ("question", "extra", "history", "ready_calls"),
    [
        ("Which hstore function returns keys in PostgreSQL 18?", {}, [], 0),
        ("Which hstore function returns keys in the latest PostgreSQL?", {}, [], 0),
        ("Which hstore function returns keys and explain its complexity?", {}, [], 0),
        ("Which hstore function returns keys?", {"persona_on": True}, [], 0),
        ("Which hstore function returns keys?", {"mode": "lesson"}, [], 0),
        ("Which hstore function returns keys?", {}, [{"role": "user", "content": "prior"}], 0),
        ("Which hstore function returns keys?", {}, [], 1),
    ],
)
async def test_fallback_preserves_context_and_skips_inference(
    question, extra, history, ready_calls
):
    project_module()
    state = SimpleNamespace(
        **{
            **dict(
                mode="neutral",
                delivery="explicit",
                persona_on=False,
                incident=None,
                active_lab=None,
            ),
            **extra,
        }
    )
    client = SimpleNamespace(
        function_lookup_ready=AsyncMock(return_value=False), function_lookup_decision=AsyncMock()
    )
    before = [dict(row) for row in history]
    assert await function_answer(question, state, object(), history, client) is None
    assert client.function_lookup_ready.await_count == ready_calls
    client.function_lookup_decision.assert_not_awaited()
    assert history == before


@pytest.mark.parametrize(
    "case", ["retrieval_error", "empty_results", "no_candidate", "unsupported_clause"]
)
async def test_missing_evidence_leaves_the_turn_to_normal_tutor(case, monkeypatch):
    import json

    from app.integrations.supabase_function_lookup import EvidenceCheck, FunctionChoice, Requirement

    project_module()
    from backend.tutor import tools

    state = SimpleNamespace(
        mode="neutral", delivery="explicit", persona_on=False, active_lab=None, incident=None
    )
    hit = {
        "url": "https://www.postgresql.org/docs/17/hstore.html",
        "content": "akeys extracts keys.",
        "tier": 2,
    }
    results = [] if case == "empty_results" else [hit]
    search = AsyncMock(
        return_value=SimpleNamespace(
            is_error=case == "retrieval_error", content=json.dumps({"results": results})
        )
    )
    monkeypatch.setattr(tools, "dispatch", search)
    choices = [
        FunctionChoice(identifier="akeys", passage=1, support="akeys extracts keys."),
        EvidenceCheck(
            requirements=[Requirement(requirement="guaranteed order", supported=False, words="")]
        ),
    ]
    decide = AsyncMock(side_effect=[None] if case == "no_candidate" else choices)
    client = SimpleNamespace(
        function_lookup_ready=AsyncMock(return_value=True), function_lookup_decision=decide
    )
    history = []
    assert (
        await function_answer(
            "Which hstore function extracts keys in guaranteed order?",
            state,
            object(),
            history,
            client,
        )
        is None
    )
    assert history == []
    assert (
        decide.await_count
        == {"retrieval_error": 0, "empty_results": 0, "no_candidate": 1, "unsupported_clause": 2}[
            case
        ]
    )
