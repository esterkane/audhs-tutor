import copy

import pytest

from app.integrations.supabase_reviewed import ReviewedOrchestrator
from app.orchestrator.saved_evidence import answer_saved_retry
from tests.test_supabase_evidence import observation, recorded
from tests.test_supabase_membership import state

QUESTION = (
    "Compare retry decisions in the first local experiment and the later minimum-zero case. "
    "Use stored observations."
)


def history():
    return recorded(observation()) + recorded(observation(minimum=0, first="b"), "call-2")


async def test_complete_source_bound_answer_needs_no_model_or_database_access():
    original = history()
    before = copy.deepcopy(original)

    class NoClientAccess:
        def __getattribute__(self, key):
            raise AssertionError("Source reuse must not access a model, key or budget")

    answer = await answer_saved_retry(QUESTION, state(), original, NoClientAccess())
    assert answer is not None
    assert "1 > 1 = false" in answer.text and "1 > 0 = true" in answer.text
    assert "original count 2" in answer.text
    assert original == before


async def test_orchestrator_appends_complete_answer_without_free_form_paraphrase():
    class Delegate:
        client = None

        async def run_turn(self, **kwargs):
            raise AssertionError("Factual report must not be paraphrased by a second model")
            yield

    from backend.tutor.orchestrator import Final

    original = history()
    before = copy.deepcopy(original)
    events = [
        event
        async for event in ReviewedOrchestrator(Delegate()).run_turn(
            user_text=QUESTION, state=state(active_lab=None), history=original, ctx=None
        )
    ]
    final = next(event for event in events if isinstance(event, Final))
    assert final.turn.next_question is None and final.turn.ledger_delta == []
    assert final.model == "local:saved-evidence.v1"
    assert final.new_messages[0] == {"role": "user", "content": QUESTION}
    assert final.new_messages[-1]["content"] == final.turn.text
    assert "**" not in final.turn.speech and "experiment1-" not in final.turn.speech
    assert original == before


@pytest.mark.parametrize(
    "changes",
    [{"mode": "exam"}, {"delivery": "socratic"}, {"incident": object()}, {"active_lab": object()}],
)
async def test_active_learning_modes_are_preserved(changes):
    assert await answer_saved_retry(QUESTION, state(**changes), history()) is None


async def test_mixed_request_falls_back_with_every_original_part_and_history_unchanged():
    from backend.tutor.orchestrator import Final

    from app.integrations.supabase_project import project_module

    question = QUESTION + " Also explain production RLS policies."
    original = history()
    seen = []

    class Delegate:
        client = None

        async def run_turn(self, **kwargs):
            seen.append(kwargs)
            turn = project_module().TutorTurn(
                mode="neutral",
                language="en",
                persona_on=False,
                text="Ordinary full answer",
                speech="Ordinary full answer",
            )
            yield Final(turn=turn, new_messages=[], model="fixture")

    events = [
        e
        async for e in ReviewedOrchestrator(Delegate()).run_turn(
            user_text=question, state=state(active_lab=None), history=original, ctx=None
        )
    ]
    assert seen[0]["user_text"] == question and seen[0]["history"] is original
    assert next(e for e in events if isinstance(e, Final)).model == "fixture"
