from types import SimpleNamespace

import pytest

from app.integrations.supabase_project import project_module
from app.integrations.supabase_questions import (
    no_quiz_requested,
    question_scope,
    questions_suppressed,
)


@pytest.mark.parametrize(
    "text",
    ["No SQL or quiz.", "Explain fully. No quiz.", "Bitte kein Quiz.", "Ohne Kontrollfragen."],
)
def test_explicit_directives(text):
    assert no_quiz_requested(text)


@pytest.mark.parametrize(
    "text",
    [
        'The document says "No quiz".',
        "> No quiz.",
        "```\nNo quiz.\n```",
        "Do not skip the quiz.",
        "Why no quiz?",
        "No quiz is missing.",
    ],
)
def test_quoted_and_negated_requests_do_not_change_delivery(text):
    assert not no_quiz_requested(text)


def test_scoped_exception_retains_other_guards_and_resets():
    module = project_module()
    from backend.tutor import guard

    state = SimpleNamespace(mode="lesson", delivery="explicit")
    turn = module.TutorTurn(
        mode="lesson",
        language="en",
        persona_on=False,
        text="An explanation.",
        speech="An explanation.",
    )
    assert any(f.code == "NO_QUESTION" for f in guard.check_questions(turn))
    with question_scope(state, "No SQL or quiz."):
        assert questions_suppressed()
        assert not any(f.code == "NO_QUESTION" for f in guard.check_questions(turn))
        questioned = turn.model_copy(update={"next_question": "What?"})
        assert any(f.code == "UNREQUESTED_QUIZ" for f in guard.check_questions(questioned))
        assert any(f.code == "QUESTION_NOT_IN_TEXT" for f in guard.check_questions(questioned))
    assert not questions_suppressed()
    assert any(f.code == "NO_QUESTION" for f in guard.check_questions(turn))


@pytest.mark.parametrize("mode,delivery", [("lesson", "socratic"), ("incident", "explicit")])
def test_other_modes_do_not_suppress(mode, delivery):
    with question_scope(SimpleNamespace(mode=mode, delivery=delivery), "No quiz."):
        assert not questions_suppressed()


async def test_concurrent_scopes_and_exception_reset():
    import asyncio

    state = SimpleNamespace(mode="lesson", delivery="explicit")

    async def scoped(text):
        with question_scope(state, text):
            await asyncio.sleep(0)
            return questions_suppressed()

    assert await asyncio.gather(scoped("No quiz."), scoped("Explain.")) == [True, False]
    with pytest.raises(RuntimeError), question_scope(state, "No quiz."):
        raise RuntimeError("test")
    assert not questions_suppressed()


def test_factual_guard_findings_survive():
    module = project_module()
    from backend.tutor import guard

    turn = module.TutorTurn(
        mode="lesson",
        language="en",
        persona_on=False,
        text="I ran the query. [9]",
        speech="I ran the query.",
    )
    context = guard.GuardContext(learner_text="Explain. No quiz.")
    before = {f.code for f in guard.check(turn, context)}
    with question_scope(SimpleNamespace(mode="lesson", delivery="explicit"), "No quiz."):
        after = {f.code for f in guard.check(turn, context)}
    assert before - {"NO_QUESTION"} == after
    assert after


@pytest.mark.parametrize("language,directive", [("en", "No quiz."), ("de", "Bitte kein Quiz.")])
async def test_local_reuse_respects_request_and_preserves_history(language, directive):
    from unittest.mock import AsyncMock

    from app.integrations.supabase_reviewed import ReviewedOrchestrator

    state = SimpleNamespace(
        mode="lesson",
        delivery="explicit",
        language=language,
        persona_on=False,
        active_lab=None,
        incident=None,
    )
    history = [{"role": "user", "content": "Earlier finding"}]
    delegate = SimpleNamespace(run_turn=AsyncMock())
    text = "Compare missing SELECT grant and RLS policy matching no rows. " + directive
    events = [
        event
        async for event in ReviewedOrchestrator(delegate).run_turn(
            state=state, user_text=text, history=history
        )
    ]
    final = events[-1]
    assert final.turn.next_question is None
    assert "?" not in final.turn.text
    assert "postgresql.org" in final.turn.text
    assert history == [{"role": "user", "content": "Earlier finding"}]
    assert final.new_messages[0]["content"] == text
    delegate.run_turn.assert_not_called()
