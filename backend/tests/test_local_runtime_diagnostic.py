"""Offline tests exercise the real response path with fake inference."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.db.models import TutorAnswer
from app.kernel import session as sessions
from app.kernel.learner import get_or_create_owner
from app.models_ai.budget import Budget
from app.models_ai.fake import FakeProvider
from app.models_ai.gateway import ModelGateway
from app.models_ai.provider import TaskClass
from app.models_ai.registry import seed_defaults
from app.models_ai.routing import Router
from app.schemas.common import Mode
from app.schemas.feedback_selection import build_passages


def module():
    path = Path(__file__).resolve().parents[2] / "scripts/eval_local_runtime.py"
    spec = importlib.util.spec_from_file_location("runtime_diagnostic", path)
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_local_settings_reject_remote_and_remove_hosted_credentials():
    diagnostic = module()
    original = Settings(openai_api_key="test-only", anthropic_api_key="test-only")
    safe = diagnostic.local_settings(original)
    assert safe.openai_api_key == safe.anthropic_api_key == ""
    assert safe.daily_budget_usd == 0
    assert original.openai_api_key == "test-only"
    with pytest.raises(ValueError, match="Loopback"):
        diagnostic.local_settings(
            original.model_copy(update={"ollama_host": "https://remote.test"})
        )


async def test_actual_runtime_saves_reuses_and_rejects_changed_work(db, settings):
    diagnostic = module()
    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    owner = await get_or_create_owner(db, display_name="test")
    session = await sessions.start(db, owner.id, mode=Mode.STEADY, energy=3)
    fake = FakeProvider(
        structured={
            "points": [
                {
                    "passage_id": build_passages(diagnostic.cases(session.id)[0][1].learner_answer)[
                        0
                    ]["id"],
                    "finding": "needs_revision",
                    "explanation": "30 divided by 50 is 0.6.",
                }
            ],
            "next_step": "Use 60%.",
            "followup_question": None,
        }
    )
    world = SimpleNamespace(settings=settings.model_copy(update={"openai_api_key": "test-only"}))

    def gateway_factory(database):
        assert world.settings.openai_api_key == world.settings.anthropic_api_key == ""
        assert world.settings.daily_budget_usd == 0
        return ModelGateway(database, Router(), {"ollama": fake}, Budget(0))

    world.gateway = gateway_factory
    gateway = await diagnostic.pinned_gateway(world, db, "llama31-8b")
    assert gateway.router.chain_for(TaskClass.ANSWER_FEEDBACK, "openai-luna") == ["llama31-8b"]
    cases = diagnostic.cases(session.id)
    invoked = []
    first = await diagnostic.evaluate_case(
        db,
        gateway,
        owner.id,
        *cases[0],
        world.settings,
        on_respond=lambda: invoked.append(True),
    )
    assert invoked == [True]
    assert first["status"] == "completed", first
    assert first["literal_schema_validated_this_run"] is True
    assert first["gateway_requests"][0]["task"] == "answer_feedback"
    assert first["attempts"][0]["registry_id"] == "llama31-8b"
    assert len(list(await db.scalars(select(TutorAnswer)))) == 1
    repeat = await diagnostic.evaluate_case(db, gateway, owner.id, *cases[1], world.settings)
    assert repeat["reply"]["reused"] is True
    assert repeat["gateway_requests"] == repeat["attempts"] == []
    assert repeat["literal_schema_validated_this_run"] is False
    fake.structured["points"][0]["passage_id"] = build_passages(cases[2][1].learner_answer)[0]["id"]
    changed = await diagnostic.evaluate_case(db, gateway, owner.id, *cases[2], world.settings)
    assert changed["reply"]["reused"] is False
    assert len(fake.calls) == 2
    assert changed["semantic_review"] == "not_reviewed"
    assert (
        first["gateway_requests"][0]["messages_sha256"]
        != changed["gateway_requests"][0]["messages_sha256"]
    )
    with pytest.raises(ValueError, match="Installed local"):
        await diagnostic.pinned_gateway(world, db, "openai-luna")

    fake.fail_times = 10
    failed = await diagnostic.evaluate_case(db, gateway, owner.id, *cases[3], world.settings)
    assert failed["status"] == "failed"
    assert failed["error_type"] == "AppError"
    assert failed["attempts"]
    assert failed["elapsed_ms"] >= 0
    assert failed["gateway_requests"][0]["elapsed_ms"] >= 0
    assert all(attempt["latency_ms"] is None for attempt in failed["attempts"])
    assert all(attempt["registry_id"] == "llama31-8b" for attempt in failed["attempts"])
    assert failed["literal_schema_validated_this_run"] is None
    assert failed["semantic_review"] == "not_reviewed"
    assert "reply" not in failed


async def test_existing_output_is_not_changed_and_setup_is_not_called(tmp_path, monkeypatch):
    diagnostic = module()
    output = tmp_path / "existing.json"
    original = b"prior evidence\n"
    output.write_bytes(original)
    monkeypatch.setattr(diagnostic, "get_settings", lambda: Settings())

    async def forbidden(*args, **kwargs):
        pytest.fail("Setup must not run when output already exists")

    monkeypatch.setattr(diagnostic, "open_world", forbidden)
    with pytest.raises(FileExistsError):
        await diagnostic.run(output, "llama31-8b")
    assert output.read_bytes() == original


async def test_setup_failure_does_not_claim_runtime_invocation(tmp_path, monkeypatch):
    diagnostic = module()
    output = tmp_path / "failed.json"
    monkeypatch.setattr(diagnostic, "get_settings", lambda: Settings())

    async def unavailable(*args, **kwargs):
        raise RuntimeError("synthetic setup failure")

    monkeypatch.setattr(diagnostic, "open_world", unavailable)
    with pytest.raises(RuntimeError, match="synthetic setup"):
        await diagnostic.run(output, "llama31-8b")
    report = json.loads(output.read_text())
    assert report["runtime_respond_exercised"] is False
    assert report["status"] == "interrupted_or_failed"
    assert report["results"] == []
    assert report["elapsed_ms"] >= 0
    assert "world cleanup" in report["timing_scope"]
    assert report["pinned_feedback_generation_model"] == "llama31-8b"


def test_notebook_suite_is_explicit_and_manifest_tracks_fixture_evidence(monkeypatch):
    diagnostic = module()
    assert [case[0] for case in diagnostic.cases("s")] == [
        "wrong_answer",
        "exact_reuse",
        "changed_answer",
        "unrun_python",
    ]
    notebook = diagnostic.cases("s", "notebook")
    assert len(notebook) == 8
    assert len({name for name, _, _ in notebook}) == 8
    by_name = {name: body for name, body, _ in notebook}
    assert by_name["unrun_pandas"].output == ""
    assert by_name["stale_output"].output_stale is True
    assert by_name["contradictory_output"].output.endswith("KeyError: ['income']")
    assert by_name["corrected_denominators"].prefer_saved is True
    assert (
        by_name["corrected_denominators"].learning_context
        == by_name["group_denominators"].learning_context
    )
    assert (
        by_name["corrected_denominators"].learner_answer
        != by_name["group_denominators"].learner_answer
    )
    original = diagnostic.suite_manifest("notebook")
    assert original["case_count"] == 8
    modified = [
        (name, body.model_copy(update={"output": "changed evidence"}), criteria)
        for name, body, criteria in notebook
    ]
    monkeypatch.setattr(diagnostic, "notebook_cases", lambda session_id: modified)
    assert diagnostic.suite_manifest("notebook")["fixture_sha256"] != original["fixture_sha256"]
    with pytest.raises(ValueError, match="Unknown diagnostic suite"):
        diagnostic.cases("s", "unknown")


async def test_notebook_supplied_work_survives_runtime_and_corrected_answer_is_not_replayed(
    db, settings
):
    diagnostic = module()
    await seed_defaults(db, installed_ollama_tags={"llama3.1:8b"})
    owner = await get_or_create_owner(db, display_name="test")
    session = await sessions.start(db, owner.id, mode=Mode.STEADY, energy=3)
    fake = FakeProvider()
    world = SimpleNamespace(settings=settings)
    world.gateway = lambda database: ModelGateway(database, Router(), {"ollama": fake}, Budget(0))
    gateway = await diagnostic.pinned_gateway(world, db, "llama31-8b")
    selected = diagnostic.cases(session.id, "notebook")
    for index in (0, 1, 5, 6):
        name, body, criteria = selected[index]
        fake.structured = {
            "points": [
                {
                    "passage_id": build_passages(body.learner_answer)[0]["id"],
                    "finding": "needs_revision",
                    "explanation": "Synthetic feedback used only to test transport.",
                }
            ],
            "next_step": "Review the supplied evidence.",
            "followup_question": None,
        }
        report = await diagnostic.evaluate_case(
            db, gateway, owner.id, name, body, criteria, world.settings
        )
        assert report["status"] == "completed", report
        assert report["reply"]["reused"] is False
        assert report["request"] == body.model_dump(exclude={"session_id"})
        assert report["manual_review_criteria"] == criteria
        assert report["semantic_review"] == "not_reviewed"
        saved = await db.get(TutorAnswer, report["reply"]["answer_id"])
        for field in ("learner_answer", "code", "output", "output_stale", "learning_context"):
            assert saved.request_json[field] == report["request"][field]
        assert (
            saved.metadata_json["quoted_feedback"]["points"][0]["learner_quote"]
            == build_passages(body.learner_answer)[0]["text"]
        )
        messages = report["gateway_requests"][0]["messages"]
        assert messages == [
            message.model_dump() for message in diagnostic.playground.messages(body)
        ]
    assert len(fake.calls) == 4


@pytest.mark.parametrize("latency, expected", [(0, None), (-1, None), (None, None), (37, 37)])
def test_attempt_diagnostic_allowlist_and_unknown_timing(latency, expected):
    diagnostic = module()
    fields = dict(
        registry_id="llama31-8b",
        model="llama3.1:8b",
        provider="ollama",
        task="answer_feedback",
        request_id="synthetic",
        attempt=2,
        outcome="invalid_output",
        tokens_in=3,
        tokens_out=4,
        cost_usd=0,
    )
    call = SimpleNamespace(
        **fields,
        latency_ms=latency,
        error="PRIVATE_ERROR_SENTINEL",
        metadata_json={
            "prompt": "PRIVATE_PROMPT_SENTINEL",
            "reply": "PRIVATE_REPLY_SENTINEL",
            "learner_answer": "PRIVATE_LEARNER_SENTINEL",
        },
    )
    result = diagnostic.attempt_diagnostic(call)
    assert result == {
        **fields,
        "latency_ms": expected,
        "structured_reason_code": "unknown",
        "latency_source": "unavailable" if expected is None else "gateway_record",
    }
    assert "PRIVATE_" not in json.dumps(result)


@pytest.mark.parametrize("fails", [False, True, "timeout"])
async def test_gateway_elapsed_is_measured_even_on_failure(monkeypatch, fails):
    diagnostic = module()
    from app.models_ai.provider import Message

    class Gateway:
        async def complete(self, *args, **kwargs):
            if fails == "timeout":
                raise TimeoutError("PRIVATE_ERROR_SENTINEL")
            if fails:
                raise RuntimeError("PRIVATE_ERROR_SENTINEL")
            return SimpleNamespace(result=SimpleNamespace(text="synthetic response"))

    ticks = iter([10.0, 12.5])
    monkeypatch.setattr(diagnostic.time, "perf_counter", lambda: next(ticks))
    recorded = diagnostic.RecordedGateway(Gateway())
    if fails:
        with pytest.raises((RuntimeError, TimeoutError)):
            await recorded.complete(
                TaskClass.ANSWER_FEEDBACK, [Message(role="user", content="synthetic")]
            )
    else:
        await recorded.complete(
            TaskClass.ANSWER_FEEDBACK, [Message(role="user", content="synthetic")]
        )
    row = recorded.requests[0]
    assert row["elapsed_ms"] == 2500
    assert row["outcome"] == ("failed_or_cancelled" if fails else "completed")
    assert "per-attempt" in row["timing_scope"]
    assert "PRIVATE_ERROR_SENTINEL" not in json.dumps(row)
    if fails:
        assert "raw_final_model_text" not in row


async def test_diagnostic_identifies_deterministic_check_not_model_validation(db, settings):
    diagnostic = module()
    owner = await get_or_create_owner(db, display_name="test")
    session = await sessions.start(db, owner.id, mode=Mode.STEADY, energy=3)
    fake = FakeProvider()
    gateway = ModelGateway(db, Router(), {"ollama": fake}, Budget(0))
    name, body, criteria = diagnostic.cases(session.id, "notebook")[2]
    report = await diagnostic.evaluate_case(db, gateway, owner.id, name, body, criteria, settings)
    assert report["status"] == "completed", report
    assert report["reply"]["route"] == "deterministic"
    assert report["literal_schema_validated_this_run"] is False
    assert report["attempts"] == []
    assert report["gateway_requests"] == []
    assert fake.calls == []
