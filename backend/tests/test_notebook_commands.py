"""Setup receipts recover acknowledgement loss without repeating installation."""

import asyncio
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.core.errors import AppError
from app.main import create_app
from app.notebooks.lab import NotebookLab


@pytest.fixture
def lab(tmp_path):
    instance = NotebookLab(Settings(_env_file=None))
    instance.root = tmp_path
    return instance


async def test_lost_ack_replays_exact_command_and_retains_completed_receipt(lab, monkeypatch):
    calls = []

    async def run(course, install):
        calls.append((course, install))
        lab.status, lab.message = "needs_install", "Install tools explicitly"

    monkeypatch.setattr(lab, "_start", run)
    key = str(uuid.uuid4())
    accepted = lab.start_command(lab.service_id, key, "first", False)
    assert accepted["request_id"] == key and accepted["status"] == "preparing"
    assert lab.start_command(lab.service_id, key, "first", False) == accepted
    await lab.task
    assert lab.lookup(lab.service_id, key)["status"] == "needs_install"
    lab.start_command(lab.service_id, str(uuid.uuid4()), "second", False)
    await lab.task
    original = lab.start_command(lab.service_id, key, "first", False)
    assert original["course_id"] == "first" and original["status"] == "needs_install"
    assert calls == [("first", False), ("second", False)]
    with pytest.raises(AppError) as raised:
        lab.start_command(lab.service_id, key, "first", True)
    assert raised.value.code == "notebook_request_conflict"


async def test_busy_other_request_is_not_accepted(lab, monkeypatch):
    gate = asyncio.Event()

    async def run(*_args):
        await gate.wait()

    monkeypatch.setattr(lab, "_start", run)
    key, other = str(uuid.uuid4()), str(uuid.uuid4())
    lab.start_command(lab.service_id, key, "first", True)
    try:
        with pytest.raises(AppError) as raised:
            lab.start_command(lab.service_id, other, "second", False)
        assert raised.value.code == "notebook_busy"
        assert other not in lab.commands
        assert lab.lookup(lab.service_id, key)["course_id"] == "first"
    finally:
        gate.set()
        await lab.task


async def test_restart_and_full_history_never_make_an_old_identity_new(lab, monkeypatch):
    async def run(*_args):
        lab.status = "needs_install"

    monkeypatch.setattr(lab, "_start", run)
    key = str(uuid.uuid4())
    with pytest.raises(AppError) as raised:
        lab.start_command(str(uuid.uuid4()), key, "first", True)
    assert raised.value.code == "notebook_outcome_unknown"
    assert lab.task is None
    for _ in range(128):
        lab.start_command(lab.service_id, str(uuid.uuid4()), "first", False)
        await lab.task
    with pytest.raises(AppError) as raised:
        lab.start_command(lab.service_id, key, "first", False)
    assert raised.value.code == "notebook_receipts_full"
    assert len(lab.commands) == 128
    with pytest.raises(AppError):
        lab.lookup(lab.service_id, key)


async def test_api_receipt_lookup_is_read_only_and_no_store(monkeypatch):
    app = create_app(Settings(auto_migrate=False, _env_file=None))
    lab = app.state.notebook_lab
    calls = []

    async def run(course, install):
        calls.append((course, install))
        lab.status, lab.message = "needs_install", "Install tools explicitly"

    monkeypatch.setattr(lab, "_start", run)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        state = (await client.get("/api/notebooks/status")).json()
        key = str(uuid.uuid4())
        body = {
            "course_id": "test",
            "install": False,
            "request_id": key,
            "service_id": state["service_id"],
        }
        response = await client.post(
            "/api/notebooks/start", json=body, headers={"X-Notebook-Action": "start"}
        )
        assert response.status_code == 200
        await lab.task
        found = await client.get(
            f"/api/notebooks/requests/{key}", params={"service_id": state["service_id"]}
        )
        assert found.status_code == 200 and found.json()["request_id"] == key
        assert found.json()["status"] == "needs_install"
        assert found.headers["cache-control"] == "no-store"
        assert calls == [("test", False)]
        missing = await client.get(
            f"/api/notebooks/requests/{uuid.uuid4()}", params={"service_id": state["service_id"]}
        )
        assert missing.status_code == 409
        mismatch = await client.post(
            "/api/notebooks/start",
            json={**body, "install": True},
            headers={"X-Notebook-Action": "start"},
        )
        assert mismatch.status_code == 409
        assert calls == [("test", False)]


async def test_old_ready_receipt_does_not_offer_a_stopped_lab(lab, monkeypatch):
    async def run(*_args):
        lab.status, lab.url = "ready", "http://127.0.0.1:8890/?token=fixture"

    monkeypatch.setattr(lab, "_start", run)
    original = str(uuid.uuid4())
    lab.start_command(lab.service_id, original, "first", False)
    await lab.task
    lab.start_command(lab.service_id, str(uuid.uuid4()), "second", False)
    await lab.task
    assert lab.lookup(lab.service_id, original)["url"] is None
    assert lab.lookup(lab.service_id, original)["status"] == "error"
