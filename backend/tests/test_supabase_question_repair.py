import copy
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.integrations import supabase_bridge as bridge
from app.integrations.supabase_project import project_module
from app.integrations.supabase_question_repair import QuestionRepair, repaired_parts
from app.models_ai.provider import ModelSpec
from tests.test_supabase_local_bridge import setup_bridge


def original_turn():
    return project_module().TutorTurn(
        mode="lesson",
        language="en",
        persona_on=False,
        text="Complete explanation.\n\nQualification and cited evidence remain.  ",
        speech="Original speech.",
    )


def test_repair_preserves_every_explanation_byte_and_other_metadata():
    turn = original_turn()
    before = turn.model_dump()
    question = QuestionRepair(
        question="If the commit happened after both reads, what would change?"
    )
    text, state = repaired_parts(turn, question)
    assert text == turn.text + "\n\n" + question.question
    expected = turn.model_dump(mode="json", exclude={"text", "guard_flags"})
    expected["next_question"] = question.question
    assert state == expected
    assert turn.model_dump() == before


@pytest.mark.parametrize("question", ["", "What now", "Why? What next?", "```SQL``` what now?"])
def test_invalid_questions_are_rejected(question):
    with pytest.raises(ValidationError):
        QuestionRepair(question=question)


async def test_hosted_question_only_call_preserves_history_and_uses_existing_gateway(monkeypatch):
    turn = original_turn()
    question = QuestionRepair(
        question="If the commit happened after both reads, what would change?"
    )
    client, call, db, _ = setup_bridge(monkeypatch, decision=question)
    hosted = SimpleNamespace(
        complete=call, spec=ModelSpec(provider="openai", model="test-only", registry_id="test-only")
    )
    monkeypatch.setattr(bridge, "choose_project_study", AsyncMock(return_value=hosted))
    history = [
        {"role": "user", "content": "Original learner request"},
        {"role": "assistant", "content": turn.text},
    ]
    before = copy.deepcopy(history)
    async with client.messages.stream(
        system=[], messages=history, tools=[], _audhs_question_repair=turn
    ) as stream:
        result = await stream.get_final_message()
    assert call.call_args.kwargs["response_model"] is QuestionRepair
    assert call.call_args.kwargs["metadata"]["question_only_repair"] is True
    sent = call.call_args.args[1]
    assert [m.content for m in sent[1:-1]] == [m["content"] for m in history]
    assert history == before
    assert result.content[0].text.startswith(turn.text + "\n\n" + question.question)
    assert db.commit.await_count >= 1


async def test_local_route_keeps_existing_full_repair(monkeypatch):
    client, call, _, _ = setup_bridge(monkeypatch)
    async with client.messages.stream(
        system=[], messages=[], tools=[], _audhs_question_repair=original_turn()
    ):
        pass
    assert call.call_args.kwargs["response_model"] is not QuestionRepair
    assert call.call_args.kwargs["metadata"]["question_only_repair"] is False


@pytest.mark.parametrize("other_failure", [False, True])
async def test_native_loop_limits_targeted_repair_to_only_missing_question(
    monkeypatch, other_failure
):
    from unittest.mock import Mock
    from uuid import uuid4

    project_module()
    from backend.tutor import guard
    from backend.tutor.orchestrator import Final, Orchestrator
    from backend.tutor.prompt import SessionState
    from backend.tutor.tools import ToolContext

    turn = original_turn()
    state = turn.model_dump(mode="json", exclude={"text", "guard_flags"})
    decision = bridge.decision_schema(()).model_validate({"text": turn.text, "state": state})
    client, call, _, _ = setup_bridge(monkeypatch, decision=decision)
    hosted = SimpleNamespace(
        complete=call, spec=ModelSpec(provider="openai", model="test-only", registry_id="test-only")
    )
    monkeypatch.setattr(bridge, "choose_project_study", AsyncMock(return_value=hosted))
    question = QuestionRepair(
        question="If the commit happened after both reads, what would change?"
    )
    outputs = [decision, decision if other_failure else question]

    async def complete(*args, **kwargs):
        return SimpleNamespace(
            result=SimpleNamespace(parsed=outputs.pop(0), tokens_in=20, tokens_out=10),
            model_call_id="test-call",
        )

    call.side_effect = complete
    failures = [guard.GuardFinding(code="NO_QUESTION", severity="block", fix_hint="Add question")]
    if other_failure:
        failures.append(
            guard.GuardFinding(code="UNCITED_CLAIM", severity="block", fix_hint="Add evidence")
        )
    checked = Mock(side_effect=[failures, []])
    monkeypatch.setattr(guard, "check", checked)
    history = [{"role": "user", "content": "Prior finding stays"}]
    before = copy.deepcopy(history)
    ctx = ToolContext(user_id=uuid4(), retriever=None, ledger=None)
    events = [
        event
        async for event in Orchestrator(client=client).run_turn(
            history=history,
            user_text="Explain this",
            state=SessionState(mode="lesson", delivery="explicit"),
            ctx=ctx,
        )
    ]
    assert checked.call_count == 2
    assert call.await_count == 2
    assert (call.call_args_list[1].kwargs["response_model"] is QuestionRepair) is (
        not other_failure
    )
    final = next(event for event in events if isinstance(event, Final))
    assert history == before
    if not other_failure:
        assert (
            final.turn.text == checked.call_args_list[0].args[0].text + "\n\n" + question.question
        )
        assert final.turn.next_question == question.question
    assert len([m for m in final.new_messages if m["role"] == "assistant"]) == 2


@pytest.mark.parametrize("speech", ["No quiz needed.", "Keine Frage nötig.", "Without a quiz."])
async def test_conflicting_speech_keeps_full_repair(monkeypatch, speech):
    turn = original_turn().model_copy(update={"speech": speech})
    client, call, _, _ = setup_bridge(monkeypatch)
    hosted = SimpleNamespace(
        complete=call, spec=ModelSpec(provider="openai", model="test-only", registry_id="test-only")
    )
    monkeypatch.setattr(bridge, "choose_project_study", AsyncMock(return_value=hosted))
    async with client.messages.stream(
        system=[], messages=[], tools=[], _audhs_question_repair=turn
    ):
        pass
    assert call.call_args.kwargs["response_model"] is not QuestionRepair
    assert not call.call_args.kwargs["metadata"]["question_only_repair"]


def test_metadata_question_becomes_visible_without_losing_any_existing_text():
    project_module()
    from backend.tutor.turn_parser import split_reply

    from app.integrations.supabase_question_repair import visible_question

    turn = original_turn().model_copy(
        update={"next_question": "What changes if the commit is later?"}
    )
    metadata = (
        bridge.decision_schema(())
        .model_validate(
            {
                "text": turn.text,
                "state": turn.model_dump(mode="json", exclude={"text", "guard_flags"}),
            }
        )
        .state
    )
    rendered = bridge.render_final_text(turn.text, metadata)
    result = visible_question(rendered, metadata)
    assert result.replace("\n\n" + turn.next_question, "", 1) == rendered
    assert turn.next_question in split_reply(result)[0]
    assert visible_question(result, metadata) == result


@pytest.mark.parametrize(
    "mode,question,text",
    [
        ("neutral", "What now?", "Explanation."),
        ("incident", "What now?", "Explanation."),
        ("lesson", "What now?", "Explanation. What now?"),
        ("lesson", "What now?", "Explanation. Why is that?"),
        ("lesson", "Why? What?", "Explanation."),
        ("lesson", None, "Explanation."),
    ],
)
def test_visible_question_does_not_invent_or_duplicate_questions(mode, question, text):
    from app.integrations.supabase_question_repair import visible_question

    turn = original_turn().model_copy(
        update={"mode": mode, "next_question": question, "text": text}
    )
    metadata = (
        bridge.decision_schema(())
        .model_validate(
            {"text": text, "state": turn.model_dump(mode="json", exclude={"text", "guard_flags"})}
        )
        .state
    )
    rendered = bridge.render_final_text(text, metadata)
    assert visible_question(rendered, metadata) == rendered


def test_visible_question_respects_no_quiz_override():
    from app.integrations.supabase_question_repair import visible_question
    from app.integrations.supabase_questions import question_scope

    turn = original_turn().model_copy(update={"next_question": "What changes?"})
    metadata = (
        bridge.decision_schema(())
        .model_validate(
            {
                "text": turn.text,
                "state": turn.model_dump(mode="json", exclude={"text", "guard_flags"}),
            }
        )
        .state
    )
    rendered = bridge.render_final_text(turn.text, metadata)
    with question_scope(SimpleNamespace(mode="lesson", delivery="explicit"), "No quiz."):
        assert visible_question(rendered, metadata) == rendered


async def test_bridge_displays_existing_question_in_one_call(monkeypatch):
    project_module()
    from backend.tutor.turn_parser import split_reply

    turn = original_turn().model_copy(
        update={"next_question": "What changes if the commit is later?"}
    )
    decision = bridge.decision_schema(()).model_validate(
        {"text": turn.text, "state": turn.model_dump(mode="json", exclude={"text", "guard_flags"})}
    )
    client, call, _, _ = setup_bridge(monkeypatch, decision=decision)
    async with client.messages.stream(system=[], messages=[], tools=[]) as stream:
        response = await stream.get_final_message()
    prose, _ = split_reply(response.content[0].text)
    assert prose.startswith(turn.text)
    assert turn.next_question in prose
    assert call.await_count == 1
