"""Request-scoped optional lesson questions; factual guards stay unchanged."""

import re
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from typing import Any

_NO_QUIZ: ContextVar[bool] = ContextVar("project_no_quiz", default=False)
_REQUEST = re.compile(
    r"(?:please\s+)?(?:no|without|skip|omit)\s+(?:sql\s+(?:or|and)\s+)?"
    r"(?:quiz|quizzes|follow-up questions?|check questions?)"
    r"|(?:bitte\s+)?(?:kein(?:e|en)?|ohne)\s+(?:quiz|kontrollfragen|rückfragen)",
    re.I,
)


def no_quiz_requested(text: str) -> bool:
    # Only standalone learner directives, not quotations, source blocks or descriptions.
    prose = re.sub(r"```.*?(?:```|$)", "", text, flags=re.S)
    prose = "\n".join(line for line in prose.splitlines() if not line.lstrip().startswith(">"))
    return any(_REQUEST.fullmatch(part.strip()) for part in re.split(r"[.!;\n]", prose))


def questions_suppressed() -> bool:
    return _NO_QUIZ.get()


def _install() -> None:
    from app.integrations.supabase_project import project_module

    project_module()
    from backend.tutor import guard

    original = guard.check_questions
    if getattr(original, "_audhs_optional_questions", False):
        return

    @wraps(original)
    def checked(turn: Any) -> Any:
        findings = original(turn)
        if not _NO_QUIZ.get():
            return findings
        findings = [finding for finding in findings if finding.code != "NO_QUESTION"]
        if turn.next_question:
            findings.append(
                guard.GuardFinding(
                    code="UNREQUESTED_QUIZ",
                    severity="block",
                    fix_hint=(
                        "The learner requested no quiz. Preserve the complete explanation and "
                        "citations; omit the follow-up quiz and set next_question to null."
                    ),
                )
            )
        return findings

    checked.__dict__["_audhs_optional_questions"] = True
    guard.check_questions = checked


@contextmanager
def question_scope(state: Any, text: str) -> Iterator[None]:
    _install()
    token = _NO_QUIZ.set(
        state.mode in {"lesson", "neutral"}
        and state.delivery == "explicit"
        and no_quiz_requested(text)
    )
    try:
        yield
    finally:
        _NO_QUIZ.reset(token)
