from types import SimpleNamespace
from unittest.mock import AsyncMock

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
