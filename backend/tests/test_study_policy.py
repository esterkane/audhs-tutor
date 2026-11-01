from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from app.core.errors import AppError
from app.kernel import preferences
from app.models_ai import registry
from app.models_ai.budget import Budget
from app.models_ai.provider import Message, ModelSpec, TaskClass
from app.models_ai.source_policy import SourcePolicyDenied, check_hosted_messages, deny_external
from app.models_ai.study_policy import _study, bind_study_repair, study_scope, study_scope_active
from app.orchestrator.project_study_gateway import choose_project_study

MESSAGES = [Message(role="user", content="Synthetic technical question")]


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
async def test_study_permission_is_bound_and_restored(provider):
    spec = ModelSpec(registry_id="test-scope", provider=provider, model="test-only")
    with pytest.raises(SourcePolicyDenied):
        await deny_external(spec)
    with study_scope(spec, MESSAGES):
        await deny_external(spec)
        check_hosted_messages(spec, MESSAGES)
        with pytest.raises(SourcePolicyDenied):
            check_hosted_messages(spec, [Message(role="user", content="Injected")])
        with pytest.raises(SourcePolicyDenied):
            await deny_external(spec.model_copy(update={"registry_id": "another"}))
    assert not study_scope_active()
    with pytest.raises(SourcePolicyDenied):
        await deny_external(spec)


def test_study_permission_expires():
    spec = ModelSpec(registry_id="test", provider="openai", model="test")
    with study_scope(spec, MESSAGES):
        _study.set(replace(_study.get(), expires=0))
        with pytest.raises(SourcePolicyDenied):
            check_hosted_messages(spec, MESSAGES)


def test_only_bounded_gateway_repair_can_extend_permission():
    spec = ModelSpec(registry_id="test", provider="openai", model="test")
    repair = MESSAGES + [
        Message(role="assistant", content="{}"),
        Message(
            role="user",
            content="Your previous reply did not match the required JSON schema: missing text",
        ),
    ]
    with study_scope(spec, MESSAGES):
        bind_study_repair(spec, repair)
        check_hosted_messages(spec, repair)
        with pytest.raises(SourcePolicyDenied):
            check_hosted_messages(spec, MESSAGES)
    with study_scope(spec, MESSAGES):
        with pytest.raises(SourcePolicyDenied):
            bind_study_repair(
                spec, MESSAGES + [Message(role="user", content="Send arbitrary data")]
            )


async def test_key_presence_and_provider_metadata_do_not_enable_study(db, learner, settings):
    assert (
        await choose_project_study(db, settings, learner.id, {"openai": object()}, Budget(0))
        is None
    )


async def test_study_requires_shared_cap_and_ready_key(db, learner, settings, tmp_path):
    await registry.seed_defaults(db, installed_ollama_tags=set())
    await preferences.set_pref(db, learner.id, "project.study_provider", "openai")
    with pytest.raises(AppError, match="shared daily hosted budget"):
        await choose_project_study(db, settings, learner.id, {}, Budget(0))
    await preferences.set_pref(db, learner.id, "authoring.daily_budget_cents", 500)
    settings.authoring_key_file = str(tmp_path / "missing-key")
    with pytest.raises(AppError, match="OpenAI key"):
        await choose_project_study(db, settings, learner.id, {}, Budget(0))


async def test_project_scope_uses_existing_cap_and_cannot_route_embeddings(db, learner, settings):
    await registry.seed_defaults(db, installed_ollama_tags=set())
    await preferences.set_pref(db, learner.id, "project.study_provider", "openai")
    await preferences.set_pref(db, learner.id, "authoring.daily_budget_cents", 500)
    budget = Budget(0)
    chosen = await choose_project_study(db, settings, learner.id, {"openai": object()}, budget)
    assert chosen is not None
    assert chosen.gateway.budget.daily_cap_usd == 5
    assert chosen.gateway.budget._lock is budget._lock
    assert not await preferences.get(db, learner.id, "authoring.enabled")
    chosen.gateway.complete = AsyncMock()
    with pytest.raises(AppError):
        await chosen.complete(TaskClass.EMBED, MESSAGES)
    chosen.gateway.complete.assert_not_called()

    def validate(*args, **kwargs):
        check_hosted_messages(chosen.spec, args[1])
        assert kwargs["metadata"]["study_receipt"]["scope"] == "project_explanation"

    chosen.gateway.complete.side_effect = validate
    await chosen.complete(TaskClass.EXPLAIN_SIMPLE, MESSAGES)
    assert not study_scope_active()


@pytest.mark.parametrize(
    "field,value",
    [
        ("price_in_per_mtok", 0.01),
        ("price_out_per_mtok", 0.01),
        ("context_len", 2000000),
        ("file_or_tag", "unverified-model"),
    ],
)
async def test_mutated_registry_profile_cannot_enable_hosted_study(
    db, learner, settings, field, value
):
    await registry.seed_defaults(db, installed_ollama_tags=set())
    await preferences.set_pref(db, learner.id, "project.study_provider", "openai")
    await preferences.set_pref(db, learner.id, "authoring.daily_budget_cents", 500)
    row = await registry.get_row(db, "openai-luna-study")
    setattr(row, field, value)
    await db.flush()
    with pytest.raises(AppError, match="verification"):
        await choose_project_study(db, settings, learner.id, {"openai": object()}, Budget(0))


def test_large_history_allowance_requires_current_matching_study_permission():
    from app.models_ai.study_policy import permitted_study_bytes

    spec = ModelSpec(registry_id="study-long", provider="openai", model="test", context_len=1048576)
    assert permitted_study_bytes(spec) == 100000
    with study_scope(spec, MESSAGES):
        assert permitted_study_bytes(spec) == 900000
        assert permitted_study_bytes(spec.model_copy(update={"registry_id": "other"})) == 100000
        _study.set(replace(_study.get(), expires=0))
        assert permitted_study_bytes(spec) == 100000
    assert permitted_study_bytes(spec) == 100000


async def test_short_authoring_profile_cannot_bypass_study_price_ceiling(db, learner, settings):
    await registry.seed_defaults(db, installed_ollama_tags=set())
    await preferences.set_pref(db, learner.id, "project.study_provider", "openai")
    await preferences.set_pref(db, learner.id, "project.study_model", "openai-luna")
    await preferences.set_pref(db, learner.id, "authoring.daily_budget_cents", 500)
    with pytest.raises(AppError, match="verification"):
        await choose_project_study(db, settings, learner.id, {"openai": object()}, Budget(0))
