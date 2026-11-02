from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.integrations import supabase_bridge as bridge
from app.integrations.supabase_reviewed import ReviewedOrchestrator
from tests.test_supabase_local_bridge import setup_bridge


async def test_neutral_discussion_does_not_execute_a_model_generated_mastery_write(monkeypatch):
    from backend.tutor.orchestrator import Orchestrator, ToolResultSummary
    from backend.tutor.prompt import SessionState
    from backend.tutor.tools import ToolContext

    decision = bridge.LocalDecision(
        tools=[
            bridge.ToolRequest(
                name="ledger_update",
                input={
                    "deltas": [
                        {
                            "topic": "rls-vs-grants",
                            "score": 5,
                            "evidence": "An invented assessment of the learner",
                        }
                    ],
                },
            )
        ]
    )
    client, _, _, _ = setup_bridge(monkeypatch, decision=decision)
    ledger = SimpleNamespace(read=AsyncMock(return_value=[]), update=AsyncMock(return_value=[]))
    ctx = ToolContext(
        user_id=uuid4(), retriever=SimpleNamespace(search=AsyncMock(return_value=[])), ledger=ledger
    )
    state = SessionState(
        mode="neutral",
        language="en",
        persona_on=False,
        delivery="explicit",
        objective="Discuss research findings",
    )
    stream = ReviewedOrchestrator(Orchestrator(client=client)).run_turn(
        history=[],
        user_text="Discuss my research findings without assessing me.",
        state=state,
        ctx=ctx,
    )
    try:
        async for event in stream:
            if isinstance(event, ToolResultSummary) and event.name == "ledger_update":
                break
    except Exception as error:
        from anthropic import APIStatusError

        assert isinstance(error, APIStatusError)
        assert error.body["error"]["code"] == "supabase_tool_invalid"
    finally:
        await stream.aclose()
    ledger.update.assert_not_awaited()


@pytest.mark.parametrize("mode", ["lesson", "exam", "incident", "rabbit_hole"])
async def test_existing_non_neutral_tool_writes_keep_original_behavior(mode):
    from backend.tutor.tools import ToolContext, TurnBudget, dispatch

    from app.integrations.supabase_progress import progress_scope

    ledger = SimpleNamespace(update=AsyncMock(return_value=[]))
    ctx = ToolContext(user_id=uuid4(), retriever=None, ledger=ledger)
    args = {
        "deltas": [
            {"topic": "rls-vs-grants", "score": 2, "evidence": "An existing assessed explanation"}
        ]
    }
    with progress_scope(SimpleNamespace(mode=mode)):
        result = await dispatch("ledger_update", args, ctx, TurnBudget())
    assert not result.is_error
    ledger.update.assert_awaited_once()


async def test_handler_denies_neutral_writes_even_when_client_tool_filter_is_bypassed():
    from backend.tutor.tools import ToolContext, TurnBudget, dispatch

    from app.integrations.supabase_progress import progress_scope

    ledger = SimpleNamespace(update=AsyncMock(return_value=[]))
    ctx = ToolContext(user_id=uuid4(), retriever=None, ledger=ledger)
    with progress_scope(SimpleNamespace(mode="neutral")):
        result = await dispatch(
            "ledger_update",
            {
                "deltas": [
                    {
                        "topic": "rls-vs-grants",
                        "score": 5,
                        "evidence": "Invented mastery without assessment",
                    }
                ]
            },
            ctx,
            TurnBudget(),
        )
    assert result.is_error and "does not assess" in result.content
    ledger.update.assert_not_awaited()


@pytest.mark.parametrize("provider", ["local", "hosted"])
def test_neutral_schema_rejects_invented_scores_and_preserves_all_other_metadata(provider):
    from app.integrations.supabase_bridge import decision_schema, hosted_decision_schema
    from app.integrations.supabase_progress import progress_schema, progress_scope

    base = decision_schema(()) if provider == "local" else hosted_decision_schema(())
    raw = {
        "text": "Complete explanation",
        "state": {
            "mode": "neutral",
            "language": "en",
            "persona_on": False,
            "speech": "Complete explanation",
            "ledger_delta": [
                {
                    "topic": "rls-vs-grants",
                    "score": 5,
                    "evidence": "Invented mastery without assessment",
                }
            ],
        },
    }
    with progress_scope(SimpleNamespace(mode="neutral")):
        schema = progress_schema(base)
        with pytest.raises(ValidationError):
            schema.model_validate(raw)
        raw["state"]["ledger_delta"] = []
        parsed = schema.model_validate(raw)
    assert parsed.text == raw["text"]
    old = base.model_json_schema()["$defs"]["SupabaseTurnMetadata"]["properties"]
    new = schema.model_json_schema()["$defs"]["UnassessedProjectMetadata"]["properties"]
    assert {k: v for k, v in old.items() if k != "ledger_delta"} == {
        k: v for k, v in new.items() if k != "ledger_delta"
    }


async def test_final_progress_guard_preserves_text_raw_history_and_real_progress_sources():
    from backend.tutor.orchestrator import Final
    from backend.tutor.prompt import SessionState

    from app.integrations.supabase_project import project_module

    text = "Complete technical answer with original examples."
    turn = project_module().TutorTurn(
        mode="neutral",
        language="en",
        persona_on=False,
        text=text,
        speech=text,
        ledger_delta=[
            {
                "topic": "rls-vs-grants",
                "score": 5,
                "evidence": "Invented mastery without assessment",
            }
        ],
    )
    raw = [
        {
            "role": "assistant",
            "content": "The original complete model response is retained for audit.",
        }
    ]

    class Delegate:
        async def run_turn(self, **kwargs):
            yield Final(turn=turn, new_messages=raw, model="fixture")

    from anthropic import APIStatusError

    with pytest.raises(APIStatusError) as failure:
        async for _ in ReviewedOrchestrator(Delegate()).run_turn(
            history=[],
            user_text="Discuss my research findings.",
            state=SessionState(mode="neutral", language="en", persona_on=False),
            ctx=None,
        ):
            pass
    assert failure.value.status_code == 422
    assert failure.value.body["error"]["code"] == "supabase_unassessed_progress"
    assert turn.text == text and len(turn.ledger_delta) == 1
    assert raw == [
        {
            "role": "assistant",
            "content": "The original complete model response is retained for audit.",
        }
    ]


async def test_progress_authority_is_task_local_and_resets_on_cancel():
    import asyncio

    from app.integrations.supabase_progress import neutral_progress, progress_scope

    async def one(mode):
        with progress_scope(SimpleNamespace(mode=mode)):
            await asyncio.sleep(0)
            assert neutral_progress() is (mode == "neutral")

    await asyncio.gather(one("neutral"), one("exam"))
    with progress_scope(SimpleNamespace(mode="neutral")):
        try:
            with progress_scope(SimpleNamespace(mode="exam")):
                raise asyncio.CancelledError
        except asyncio.CancelledError:
            pass
        assert neutral_progress()
    assert not neutral_progress()


@pytest.mark.parametrize("known", [True, False])
async def test_stream_boundary_adapts_only_safe_host_errors(known):
    from anthropic import APIStatusError
    from backend.tutor.prompt import SessionState

    from app.core.errors import AppError

    original = (
        AppError("supabase_tool_invalid", "Invalid tool request.", 422)
        if known
        else RuntimeError("unexpected")
    )

    class Delegate:
        async def run_turn(self, **kwargs):
            raise original
            yield  # Async iterator, without a successful final event.

    with pytest.raises(APIStatusError if known else RuntimeError) as failure:
        async for _ in ReviewedOrchestrator(Delegate()).run_turn(
            history=[],
            user_text="Discuss my research findings.",
            state=SessionState(mode="neutral", language="en", persona_on=False),
            ctx=None,
        ):
            pytest.fail("Failed turns must not emit accepted events")
    if known:
        assert failure.value.status_code == 422
        assert failure.value.message == original.message
        assert failure.value.__cause__ is original
    else:
        assert failure.value is original
