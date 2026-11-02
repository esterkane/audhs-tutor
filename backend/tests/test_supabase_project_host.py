from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.integrations import supabase_project as host


async def test_unconfigured_host_does_not_open_a_service(monkeypatch):
    app = SimpleNamespace(
        state=SimpleNamespace(
            settings=SimpleNamespace(supabase_project_db_url="", supabase_project_user_id=""),
            tutor=None,
        )
    )

    def unexpected():
        raise AssertionError("Must not open an unconfigured project")

    monkeypatch.setattr(host, "project_module", unexpected)
    await host.open_project(app)
    assert app.state.tutor is None


async def test_partial_startup_closes_resources_and_redacts_private_error(monkeypatch):
    secret = "private-database-password"
    service = SimpleNamespace(
        orchestrator=lambda user_id=None: SimpleNamespace(),
        open=AsyncMock(),
        close=AsyncMock(),
        app_pool=SimpleNamespace(wait=AsyncMock(side_effect=RuntimeError(secret))),
        lab_pool=SimpleNamespace(wait=AsyncMock()),
    )
    project = SimpleNamespace(
        HostConfig=lambda **kwargs: kwargs, build_service=lambda config: service
    )
    monkeypatch.setattr(host, "project_module", lambda: project)
    settings = SimpleNamespace(
        supabase_project_db_url=secret,
        supabase_project_user_id="12345678-1234-5678-1234-567812345678",
        supabase_project_url="http://127.0.0.1:54321",
        daily_budget_usd=0,
    )
    app = SimpleNamespace(
        state=SimpleNamespace(settings=settings, tutor=None, session_factory=None, providers={})
    )
    await host.open_project(app)
    service.close.assert_awaited_once()
    assert app.state.tutor is None
    assert secret not in app.state.supabase_project_error
    assert "RuntimeError" in app.state.supabase_project_error


async def test_successful_startup_waits_for_both_pools(monkeypatch):
    service = SimpleNamespace(
        orchestrator=lambda user_id=None: SimpleNamespace(),
        open=AsyncMock(),
        close=AsyncMock(),
        app_pool=SimpleNamespace(wait=AsyncMock()),
        lab_pool=SimpleNamespace(wait=AsyncMock()),
    )
    project = SimpleNamespace(
        HostConfig=lambda **kwargs: kwargs, build_service=lambda config: service
    )
    monkeypatch.setattr(host, "project_module", lambda: project)
    settings = SimpleNamespace(
        supabase_project_db_url="test-only",
        supabase_project_user_id="12345678-1234-5678-1234-567812345678",
        supabase_project_url="http://127.0.0.1:54321",
        daily_budget_usd=0,
    )
    app = SimpleNamespace(
        state=SimpleNamespace(settings=settings, tutor=None, session_factory=None, providers={})
    )
    await host.open_project(app)
    assert app.state.tutor is service
    assert app.state.supabase_project_error is None
    service.app_pool.wait.assert_awaited_once()
    service.lab_pool.wait.assert_awaited_once()
    await host.close_project(app)
    service.close.assert_awaited_once()


async def test_status_reports_owner_selected_provider_without_enabling_from_key(
    db, learner, settings
):
    from app.kernel import preferences

    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(settings=settings, tutor=None, supabase_project_error=None)
        )
    )
    result = await host.status(request, db, learner)
    assert result["study_provider"] == "local"
    assert result["hosted_study_enabled"] is False
    await preferences.set_pref(db, learner.id, "project.study_provider", "openai")
    result = await host.status(request, db, learner)
    assert result["study_provider"] == "openai"
    assert result["hosted_study_enabled"] is True


@pytest.mark.parametrize("model", ["openai-luna-study", "openai-sol-study"])
async def test_study_choice_saves_provider_and_model_together_without_inference(
    db, learner, settings, model
):
    from app.kernel import preferences

    await preferences.set_pref(db, learner.id, "authoring.daily_budget_cents", 500)
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                settings=settings,
                providers={"openai": object()},
                tutor=None,
                supabase_project_error=None,
            )
        )
    )
    result = await host.set_study(
        host.ProjectStudyChoice(provider="openai", model=model), request, db, learner
    )
    assert result["study_model"] == model
    assert result["study_provider"] == "openai"
    assert await preferences.get(db, learner.id, "project.study_model") == model
    result = await host.set_study(host.ProjectStudyChoice(provider="local"), request, db, learner)
    assert result["study_provider"] == "local"
    assert await preferences.get(db, learner.id, "authoring.daily_budget_cents") == 500


async def test_failed_provider_setup_preserves_previous_choice(db, learner, settings):
    import pytest

    from app.core.errors import AppError
    from app.kernel import preferences

    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                settings=settings, providers={}, tutor=None, supabase_project_error=None
            )
        )
    )
    with pytest.raises(AppError, match="shared daily hosted budget"):
        await host.set_study(host.ProjectStudyChoice(provider="openai"), request, db, learner)
    assert await preferences.get(db, learner.id, "project.study_provider") == "local"
