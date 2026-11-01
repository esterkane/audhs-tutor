import copy
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.integrations import supabase_isolation as adapter
from app.integrations.supabase_project import project_module
from app.integrations.supabase_reviewed import ReviewedOrchestrator
from tests.test_supabase_membership import context, state

project_module()
from backend.tutor.schemas import Chunk  # noqa: E402

QUESTION = "Compare transaction isolation locally for 2 active workers, minimum 1, attempting A's commit first."
GERMAN = "Vergleiche Transaktionsisolation lokal mit 2 aktiven Kräften, mindestens 1, und Commit-Versuch A zuerst."
URL = "https://www.postgresql.org/docs/17/transaction-iso.html"


def observed():
    tx = {
        "a": {"read": {"count": 2}, "updated": 1, "committed": True, "error": None},
        "b": {"read": {"count": 2}, "updated": 1, "committed": True, "error": None},
    }
    runs = []
    for level, retry in (
        ("read committed", "none"),
        ("repeatable read", "none"),
        ("serializable", "none"),
        ("serializable", "full"),
        ("serializable", "update_only"),
    ):
        transactions = copy.deepcopy(tx)
        if level == "serializable":
            transactions["b"].update(
                committed=False, error={"sqlstate": "40001", "stage": "commit"}
            )
        retried = None
        count = 1 if level == "serializable" else 0
        if retry != "none":
            retried = {
                "read": {"count": 1} if retry == "full" else None,
                "decision": retry != "full",
            }
            count = 1 if retry == "full" else 0
        runs.append(
            {
                "level": level,
                "retry_strategy": retry,
                "transactions": transactions,
                "final_active": count,
                "minimum_satisfied": count >= 1,
                "retry": retried,
            }
        )
    return {
        "database": "lab",
        "server_version": "17.11",
        "schema_removed": True,
        "input": {"workers": 2, "minimum_active": 1, "first_commit": "a"},
        "runs": runs,
    }


def configured_context(url=URL, tier=3):
    ctx = context({})
    ctx.lab.lab_url = "postgresql://localhost/lab"
    ctx.retriever.search.return_value = [
        Chunk(
            chunk_id=uuid4(),
            url=url,
            heading_path="Transaction isolation",
            content="Synthetic official reference.",
            tier=tier,
            score=1,
            fetched_at=None,
            anchor=None,
        )
    ]
    return ctx


@pytest.mark.parametrize("question", [QUESTION, GERMAN])
def test_explicit_bilingual_commands_preserve_parameters(question):
    assert adapter.parse_request(question).model_dump() == observed()["input"]


@pytest.mark.parametrize(
    "question",
    [
        "Explain transaction isolation",
        QUESTION + " Also inspect users.",
        "Do not execute anything: " + QUESTION,
    ],
)
def test_other_questions_are_not_intercepted(question):
    assert adapter.parse_request(question) is None


def test_invalid_literal_count_cannot_enter_the_engine():
    with pytest.raises(ValidationError):
        adapter.parse_request(QUESTION.replace("2 active", "999 active"))


@pytest.mark.parametrize("language,question", [("en", QUESTION), ("de", GERMAN)])
async def test_actual_evidence_and_source_are_saved_without_model_or_history_loss(
    monkeypatch, language, question
):
    evidence = observed()
    run = AsyncMock(return_value=evidence)
    monkeypatch.setattr(adapter, "run_isolation_experiment", run)
    ctx = configured_context()
    before = copy.deepcopy(evidence)
    answer = await adapter.isolation_answer(question, state(language=language), ctx)
    assert answer.turn.next_question is None and not answer.turn.ledger_delta
    assert "40001" in answer.turn.text and "1 > 1" in answer.turn.text
    assert (
        "A before B and B before A" in answer.turn.text
        if language == "en"
        else "A vor B und zugleich B vor A" in answer.turn.text
    )
    assert [c.url for c in answer.turn.citations] == [URL]
    assert "[1]" in answer.turn.text
    assert evidence == before
    recorded = json.loads(answer.messages[2]["content"][0]["content"])
    assert recorded == before
    assert answer.messages[0]["content"] == question
    assert [c[0] for c in answer.calls] == ["compare_isolation_lab", "search_docs"]
    run.assert_awaited_once()


@pytest.mark.parametrize("url,tier", [(URL.replace("/17/", "/16/"), 3), (URL, 4)])
async def test_other_versions_and_community_cannot_become_manual_citations(monkeypatch, url, tier):
    monkeypatch.setattr(adapter, "run_isolation_experiment", AsyncMock(return_value=observed()))
    result = await adapter.isolation_answer(QUESTION, state(), configured_context(url, tier))
    assert not result.turn.citations
    assert "40001" in result.turn.text


async def test_documentation_outage_retains_measured_results(monkeypatch):
    monkeypatch.setattr(adapter, "run_isolation_experiment", AsyncMock(return_value=observed()))
    ctx = configured_context()
    ctx.retriever.search.side_effect = RuntimeError("Synthetic source outage")
    result = await adapter.isolation_answer(QUESTION, state(), ctx)
    assert "40001" in result.turn.text and not result.turn.citations
    assert result.calls[-1][2] is True


async def test_wrong_input_echo_is_not_accepted(monkeypatch):
    evidence = observed()
    evidence["input"]["workers"] = 3
    monkeypatch.setattr(adapter, "run_isolation_experiment", AsyncMock(return_value=evidence))
    ctx = configured_context()
    result = await adapter.isolation_answer(QUESTION, state(), ctx)
    assert "No outcomes were accepted" in result.turn.text
    assert result.calls[0][2] is True
    ctx.retriever.search.assert_not_awaited()


@pytest.mark.parametrize(
    "changes", [{"mode": "lesson"}, {"delivery": "socratic"}, {"incident": object()}]
)
async def test_other_learning_modes_do_not_execute_the_experiment(monkeypatch, changes):
    run = AsyncMock()
    monkeypatch.setattr(adapter, "run_isolation_experiment", run)
    assert await adapter.isolation_answer(QUESTION, state(**changes), configured_context()) is None
    run.assert_not_awaited()


async def test_reviewed_adapter_returns_complete_computed_turn_and_preserves_history(monkeypatch):
    monkeypatch.setattr(adapter, "run_isolation_experiment", AsyncMock(return_value=observed()))
    delegate = SimpleNamespace(run_turn=AsyncMock())
    history = [{"role": "user", "content": "Earlier finding remains unchanged."}]
    before = copy.deepcopy(history)
    events = [
        event
        async for event in ReviewedOrchestrator(delegate).run_turn(
            user_text=QUESTION, state=state(), ctx=configured_context(), history=history
        )
    ]
    assert events[-1].model == "local:isolation-lab.v1"
    assert "40001" in events[-1].turn.text
    assert history == before
    delegate.run_turn.assert_not_called()


@pytest.mark.parametrize("german", [False, True])
def test_no_write_trial_does_not_invent_updates_or_retry_failures(german):
    evidence = observed()
    evidence["input"]["minimum_active"] = 2
    for run in evidence["runs"]:
        run.update(final_active=2, minimum_satisfied=True, retry=None)
        for transaction in run["transactions"].values():
            transaction.update(updated=0, committed=True, error=None)
    text = adapter.render(evidence, german)
    assert ("kein UPDATE gesendet" if german else "no UPDATE was sent") in text
    assert ("Hier war kein Retry nötig" if german else "No retry was needed") in text


def test_unperformed_retry_is_not_described_as_no_serialization_failure():
    evidence = observed()
    evidence["runs"][3]["retry"] = None
    text = adapter.render(evidence, False)
    assert "did not execute a retry" in text
    assert "No retry was needed" not in text
