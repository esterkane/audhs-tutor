"""Readiness checks use temporary files and metadata mocks; never real services or credentials."""

import asyncio
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from app.core.config import Settings
from app.core.doctor import credential_storage, database, diagnose, local_url


@pytest.fixture
def diagnostic_settings(tmp_path):
    database_file = tmp_path / "diagnostic.db"
    with sqlite3.connect(database_file) as c:
        c.execute("CREATE TABLE learner_profile (id TEXT)")
        c.execute("CREATE TABLE alembic_version (version_num TEXT)")
    folder = tmp_path / "private"
    folder.mkdir()
    key = folder / "authoring.key"
    key.write_text("synthetic-fixture-not-a-credential")
    key.chmod(0o600)
    return Settings(
        database_url=f"sqlite+aiosqlite:///{database_file}",
        authoring_key_file=str(key),
        openai_api_key="",
        anthropic_api_key="",
        _env_file=None,
    )


def healthy(request):
    if request.url.path == "/api/health":
        return httpx.Response(200, json={"status": "ok", "db": "ok"})
    if request.url.path == "/api/tags":
        return httpx.Response(200, json={"models": [{"name": "fixture"}]})
    if request.url.path == "/readyz":
        return httpx.Response(200, text="all components are ready")
    raise AssertionError("Non-metadata request")


@pytest.mark.parametrize("mode", ["local", "authoring"])
async def test_healthy_is_read_only(diagnostic_settings, tmp_path, mode):
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    with patch.object(
        Settings, "read_authoring_key", side_effect=AssertionError("must not read key")
    ):
        report = await diagnose(
            diagnostic_settings, mode=mode, transport=httpx.MockTransport(healthy)
        )
    assert report.status == "healthy" and report.exit_code == 0
    after = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after
    assert "synthetic-fixture" not in report.model_dump_json()
    assert str(tmp_path) not in report.model_dump_json()


async def test_optional_services_are_degraded_for_authoring(diagnostic_settings):
    def handler(request):
        return healthy(request) if request.url.path == "/api/health" else httpx.Response(503)

    report = await diagnose(
        diagnostic_settings, mode="authoring", transport=httpx.MockTransport(handler)
    )
    assert report.status == "degraded" and report.exit_code == 1
    assert [c.status for c in report.checks[:3]] == ["ok", "warning", "warning"]


async def test_required_service_failure(diagnostic_settings):
    def handler(request):
        raise httpx.ConnectError("SECRET must not appear", request=request)

    report = await diagnose(diagnostic_settings, transport=httpx.MockTransport(handler))
    assert report.status == "unavailable" and report.exit_code == 2
    assert "SECRET" not in report.model_dump_json()


async def test_total_probe_timeout(diagnostic_settings):
    async def handler(request):
        await asyncio.sleep(1)
        return healthy(request)

    report = await asyncio.wait_for(
        diagnose(diagnostic_settings, timeout_s=0.1, transport=httpx.MockTransport(handler)), 1
    )
    assert all(c.code == "unreachable" for c in report.checks[:3])


@pytest.mark.parametrize(
    "url",
    [
        "https://remote.example",
        "http://localhost@remote.example",
        "http://127.0.0.1/proxy",
        "http://localhost?key=SECRET",
        "http://localhost:0",
        "http://localhost:bad",
    ],
)
async def test_unsafe_api_endpoints_never_contacted(diagnostic_settings, url):
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return healthy(request)

    report = await diagnose(
        diagnostic_settings, api_url=url, transport=httpx.MockTransport(handler)
    )
    assert report.checks[0].code == "unsafe_endpoint"
    assert len(seen) == 2 and "SECRET" not in report.model_dump_json()


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(302, headers={"Location": "https://remote.example"}),
        httpx.Response(200, text="not JSON"),
        httpx.Response(200, json=[]),
        httpx.Response(200, text="x" * 65537),
    ],
)
async def test_bad_metadata_no_redirects(diagnostic_settings, response):
    seen = []

    def handler(request):
        seen.append(request.url.host)
        return response if request.url.path == "/api/health" else healthy(request)

    report = await diagnose(diagnostic_settings, transport=httpx.MockTransport(handler))
    assert report.checks[0].status == "error" and "remote.example" not in seen


def test_missing_database_not_created(diagnostic_settings, tmp_path):
    path = tmp_path / "absent.db"
    diagnostic_settings.database_url = f"sqlite+aiosqlite:///{path}"
    assert database(diagnostic_settings, 0.1).code == "missing_database"
    assert not path.exists()


def test_corrupt_and_empty_schema(diagnostic_settings, tmp_path):
    path = tmp_path / "corrupt.db"
    path.write_bytes(b"not a sqlite database")
    diagnostic_settings.database_url = f"sqlite+aiosqlite:///{path}"
    assert database(diagnostic_settings, 0.1).code == "unreadable_database"
    path = tmp_path / "empty.db"
    with sqlite3.connect(path) as c:
        c.execute("CREATE TABLE unrelated (id TEXT)")
    diagnostic_settings.database_url = f"sqlite+aiosqlite:///{path}"
    assert database(diagnostic_settings, 0.1).code == "schema_missing"


def test_missing_and_unwritable_key_directory(diagnostic_settings, tmp_path):
    with patch("app.core.doctor.os.access", return_value=False):
        checks = credential_storage(diagnostic_settings, True)
    assert checks[0].code == "key_directory_unwritable" and checks[0].status == "error"
    diagnostic_settings.authoring_key_file = str(tmp_path / "not-created" / "key")
    assert credential_storage(diagnostic_settings, True)[0].code == "missing_key_directory"
    assert not (tmp_path / "not-created").exists()


def test_key_missing_and_symlink(diagnostic_settings, tmp_path):
    path = Path(diagnostic_settings.authoring_key_file)
    path.unlink()
    assert credential_storage(diagnostic_settings, True)[-1].code == "key_missing_or_unreadable"
    target = tmp_path / "target"
    target.write_text("do not read")
    path.symlink_to(target)
    assert credential_storage(diagnostic_settings, True)[0].code == "unsafe_key_path"


@pytest.mark.parametrize("value", [0, 11, float("nan")])
async def test_timeout_validation(diagnostic_settings, value):
    with pytest.raises(ValueError):
        await diagnose(diagnostic_settings, timeout_s=value)


def test_loopback_ipv6():
    assert local_url("http://[::1]:8000", "/api/health") == "http://[::1]:8000/api/health"


def test_cli_sanitizes_invalid_settings(tmp_path):
    import os

    root = Path(__file__).resolve().parents[2]
    env = {**os.environ, "DAILY_BUDGET_USD": "synthetic-sensitive-value"}
    result = subprocess.run(
        [sys.executable, "-B", str(root / "scripts/doctor.py"), "--json"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2 and json.loads(result.stdout)["status"] == "unavailable"
    assert "synthetic-sensitive-value" not in result.stdout + result.stderr


async def test_empty_ollama_is_not_healthy_local_study(diagnostic_settings):
    def handler(request):
        return (
            httpx.Response(200, json={"models": []})
            if request.url.path == "/api/tags"
            else healthy(request)
        )

    report = await diagnose(diagnostic_settings, transport=httpx.MockTransport(handler))
    assert report.checks[1].code == "no_installed_models" and report.status == "unavailable"
