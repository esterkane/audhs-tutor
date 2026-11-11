"""Reviewed reuse and explicit fixed-query labs; no model-invented SQL or mastery updates."""

import re
from collections.abc import AsyncIterator
from typing import Any

from app.integrations.supabase_output_constraints import no_sql_requested

SOURCES = (
    "https://www.postgresql.org/docs/17/ddl-rowsecurity.html",
    "https://www.postgresql.org/docs/17/functions-info.html",
)
# Read-only examples deliberately use catalog OIDs, never model-invented identifiers.
DIAGNOSTICS = """SELECT current_user;
SELECT n.nspname, c.relname,
       has_schema_privilege(current_user, n.oid, 'USAGE') AS schema_usage,
       has_table_privilege(current_user, c.oid, 'SELECT') AS table_select,
       c.relrowsecurity, c.relforcerowsecurity
FROM pg_class AS c
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p');
SELECT schemaname, tablename, policyname, roles, cmd, qual, with_check
FROM pg_policies WHERE schemaname = 'public';"""


def matches(text: str, state: Any) -> bool:
    """Only direct requests for this distinction; no exam/incident/lab bypass."""
    if state.delivery != "explicit" or state.mode not in {"lesson", "neutral"}:
        return False
    if state.active_lab is not None or state.incident is not None:
        return False
    if len(text) > 1400 or "```" in text:
        return False
    lower = text.casefold()
    # Decline broader operations, user SQL and instructions requesting a different output.
    if re.search(
        r"\b(insert|update|delete|create|alter|drop|truncate|function|trigger|view|join|explain analyze)\b",
        lower,
    ):
        return False
    return bool(
        re.search(r"difference|distinguish|compare|unterschied|unterscheid|vergleiche", lower)
        and re.search(r"\bselect\b", lower)
        and re.search(r"grant|privilege|berechtigung", lower)
        and re.search(r"policy|policies|rls|richtlinie", lower)
        and re.search(r"no rows|zero rows|empty result|keine zeilen|leere.*ergebnis", lower)
    )


def reviewed_turn(
    state: Any, *, include_diagnostics: bool = True, include_question: bool = True
) -> Any:
    from app.integrations.supabase_project import project_module

    module = project_module()
    if state.language == "de":
        explanation = (
            "Tabellenberechtigungen und Zeilenrichtlinien sind zwei getrennte Prüfungen. "
            "Fehlt die nötige SELECT-Berechtigung, kann der Zugriff mit permission denied scheitern. "
            "Sind die nötigen Berechtigungen vorhanden, liefert ein normales SELECT bei einer "
            "RLS-Richtlinie ohne passende Zeilen normalerweise ein leeres Ergebnis. Diese Zeilenfilterung "
            "allein erklärt keinen Fehler wegen fehlender Tabellenberechtigung.\n\n"
            "Prüfe mit der tatsächlichen Anwendungsrolle. Eigentümer und Rollen mit BYPASSRLS können "
            "die Zeilenrichtlinien umgehen; auch Funktionen in Richtlinien können eigene Fehler auslösen."
        )
        diagnostic_note = (
            "Die folgenden Abfragen sind Beispiele zur Einsicht in Berechtigungen und Richtlinien. "
            "Sie wurden nicht gegen deine Datenbank ausgeführt und simulieren keine JWT-Identität."
        )
        question = "Welche Prüfung würdest du zuerst durchführen, und warum?"
        speech = (
            "Tabellenberechtigungen erlauben eine Operation. "
            "Zeilenrichtlinien begrenzen die sichtbaren Zeilen. "
            "Prüfe beides mit der tatsächlichen Anwendungsrolle."
        )
    else:
        explanation = (
            "Table privileges and row policies are separate checks. Missing required SELECT privileges "
            "can produce permission denied. With the required privileges, an ordinary SELECT under "
            "an RLS policy admitting no rows normally returns an empty result. That row filtering "
            "alone does not explain a table permission-denied error.\n\n"
            "Check as the actual application role. Owners and roles with BYPASSRLS can bypass row "
            "policies; functions inside a policy can also raise their own errors."
        )
        diagnostic_note = (
            "These read-only queries inspect privileges and policies. "
            "They have not been run against your database and do not simulate a JWT identity."
        )
        question = "Which check would you make first, and why?"
        speech = (
            "Table privileges permit an operation. Row policies restrict visible rows. "
            "Check both as the actual application role."
        )
    text = explanation
    if include_diagnostics:
        text += " " + diagnostic_note + "\n\n```sql\n" + DIAGNOSTICS + "\n```"
    if state.mode != "neutral" and include_question:
        text += "\n\n" + question
    text += "\n\n" + "\n".join(SOURCES)
    return module.TutorTurn(
        mode=state.mode,
        language=state.language,
        persona_on=state.persona_on,
        speech=speech,
        text=text,
        next_question=question if state.mode != "neutral" and include_question else None,
    )


class ReviewedOrchestrator:
    """Preserve ordinary orchestrator and append-only messages for all other requests."""

    def __init__(self, delegate: Any) -> None:
        self.delegate = delegate

    async def run_turn(self, **kwargs: Any) -> AsyncIterator[Any]:
        from app.integrations.supabase_mode import mode_scope, selected_state
        from app.integrations.supabase_vector_evidence import install_vector_evidence

        install_vector_evidence()
        user_text = kwargs["user_text"]
        state = selected_state(kwargs["state"], user_text)
        kwargs = {**kwargs, "state": state}
        from backend.tutor.orchestrator import Final, Token, ToolCall, ToolResultSummary

        from app.integrations.supabase_mode import standalone_mode

        if standalone_mode(user_text) is not None:
            from app.integrations.supabase_project import project_module

            labels = {
                "en": {
                    "lesson": "Lesson",
                    "exam": "Exam",
                    "neutral": "Neutral",
                    "incident": "Incident",
                    "rabbit_hole": "Exploration",
                },
                "de": {
                    "lesson": "Lernen",
                    "exam": "Prüfung",
                    "neutral": "Neutral",
                    "incident": "Fehlersuche",
                    "rabbit_hole": "Vertiefung",
                },
            }
            label = labels[state.language][state.mode]
            text = f"Modus: {label}." if state.language == "de" else f"Mode: {label}."
            turn = project_module().TutorTurn(
                mode=state.mode,
                language=state.language,
                persona_on=state.persona_on,
                text=text,
                speech=text,
            )
            yield Token(text)
            yield Final(
                turn=turn,
                new_messages=[
                    {"role": "user", "content": user_text},
                    {"role": "assistant", "content": text},
                ],
                model="local:mode-command.v1",
            )
            return

        from app.integrations.supabase_balance import balance_answer
        from app.integrations.supabase_incidents import (
            first_evidence_question,
            incident_turn,
            select_plan,
        )
        from app.integrations.supabase_isolation import isolation_answer
        from app.integrations.supabase_membership import membership_answer
        from app.integrations.supabase_reference import reference_answer, supports_manual

        isolation = await balance_answer(user_text, state, kwargs.get("ctx"), kwargs.get("history"))
        lab_model = "local:same-row-balance-lab.v1"
        if isolation is None:
            isolation = await isolation_answer(
                user_text, state, kwargs.get("ctx"), kwargs.get("history")
            )
            lab_model = "local:isolation-lab.v1"
        if isolation is not None:
            for name, args, is_error in isolation.calls:
                yield ToolCall(name, args)
                yield ToolResultSummary(name, is_error, "Local transaction experiment evidence.")
            yield Token(isolation.turn.text)
            yield Final(turn=isolation.turn, new_messages=isolation.messages, model=lab_model)
            return

        membership = await membership_answer(
            user_text, state, kwargs.get("ctx"), kwargs.get("history")
        )
        if membership is not None:
            for name, args, is_error in membership.calls:
                yield ToolCall(name, args)
                yield ToolResultSummary(name, is_error, "Local literal-value comparison evidence.")
            yield Token(membership.turn.text)
            yield Final(
                turn=membership.turn,
                new_messages=membership.messages,
                model="local:membership-lab.v1",
            )
            return

        reference = await reference_answer(
            user_text, state, kwargs.get("ctx"), kwargs.get("history")
        )
        if reference is not None:
            yield ToolCall("search_docs", reference.messages[1]["content"][0]["input"])
            yield ToolResultSummary("search_docs", False, reference.summary)
            yield Token(reference.turn.text)
            yield Final(
                turn=reference.turn,
                new_messages=reference.messages,
                model=reference.model,
            )
            return

        from app.orchestrator.saved_evidence import answer_saved_retry

        saved = await answer_saved_retry(
            user_text, state, kwargs.get("history", []), getattr(self.delegate, "client", None)
        )
        if saved is not None:
            from app.integrations.supabase_project import project_module

            turn = project_module().TutorTurn(
                mode=state.mode,
                language=state.language,
                persona_on=state.persona_on,
                text=saved.text,
                speech="\n".join(
                    line
                    for line in saved.text.splitlines()
                    if not line.startswith(("Source:", "Quelle:"))
                )
                .replace("**", "")
                .replace("`", ""),
            )
            yield Token(turn.text)
            yield Final(
                turn=turn,
                new_messages=[
                    {"role": "user", "content": user_text},
                    {"role": "assistant", "content": saved.text},
                ],
                model="local:saved-retry-reasoning.v1"
                if saved.method == "literal-reference-causal-proof.v1"
                else "local:saved-evidence.v1",
            )
            return

        plan = select_plan(user_text, state)
        can_use_reviewed = (plan is not None or matches(user_text, state)) and supports_manual(
            "17", user_text, state, kwargs.get("history")
        )
        opening_question = first_evidence_question(user_text, state, kwargs.get("history"))
        if opening_question:
            from app.integrations.supabase_project import project_module

            turn = project_module().TutorTurn(
                mode=state.mode,
                language=state.language,
                persona_on=state.persona_on,
                text=opening_question,
                speech=opening_question,
                next_question=opening_question,
            )
            revision = "reviewed:incident-first-observation.v1"
        elif can_use_reviewed and plan is not None:
            turn = incident_turn(
                user_text, state, plan, include_diagnostics=not no_sql_requested(user_text)
            )
            revision = "reviewed:incident-" + plan.key + ".v2"
        elif can_use_reviewed:
            from app.integrations.supabase_questions import no_quiz_requested

            turn = reviewed_turn(
                state,
                include_diagnostics=not no_sql_requested(user_text),
                include_question=not no_quiz_requested(user_text),
            )
            revision = "reviewed:select-privileges-row-visibility.v2"
        else:
            from anthropic import APIStatusError
            from httpx2 import Request, Response

            from app.core.errors import AppError
            from app.integrations.supabase_progress import progress_scope, validate_progress
            from app.integrations.supabase_questions import question_scope

            try:
                with mode_scope(state), progress_scope(state), question_scope(state, user_text):
                    async for event in self.delegate.run_turn(**kwargs):
                        if isinstance(event, Final):
                            validate_progress(event.turn)
                        yield event
            except AppError as error:
                # The pinned router already encodes SDK status errors as SSE errors.
                # Adapt host failures before they reach HTTP exception handlers after
                # streaming has started. No Final is yielded or persisted on failure.
                raise APIStatusError(
                    error.message,
                    response=Response(
                        error.http_status,
                        request=Request("POST", "http://localhost/supabase-project/turn"),
                    ),
                    body={"error": {"code": error.code, "message": error.message}},
                ) from error
            return
        yield Token(turn.text)
        yield Final(
            turn=turn,
            new_messages=[
                {"role": "user", "content": user_text},
                {"role": "assistant", "content": turn.text},
            ],
            model=revision,
        )
