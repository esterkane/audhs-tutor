import asyncio
import json
import os
import shutil
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app
from app.notebooks.lab import NotebookLab, prepare


def bundle(root: Path) -> Path:
    folder = root / "frontend/public/local-learning"
    folder.mkdir(parents=True)
    (folder / "task.ipynb").write_text('{"nbformat":4,"cells":[]}')
    (folder / "data.csv").write_text("x\n1\n")
    (folder / "program.json").write_text(
        json.dumps(
            {
                "courses": [
                    {
                        "id": "test",
                        "lab_files": [
                            {"source": "task.ipynb", "name": "task.ipynb"},
                            {"source": "data.csv", "name": "data.csv"},
                        ],
                    }
                ]
            }
        )
    )
    return folder


def test_prepare_preserves_edits_and_copies_dataset(tmp_path: Path) -> None:
    bundle(tmp_path)
    assert prepare(tmp_path, "test") == "test/task.ipynb"
    target = tmp_path / "data/notebooks/test/task.ipynb"
    target.write_text("learner edits")
    prepare(tmp_path, "test")
    assert target.read_text() == "learner edits"
    assert (target.parent / "data.csv").read_text() == "x\n1\n"


@pytest.mark.parametrize("field,value", [("source", "../../../../secret"), ("name", "../secret")])
def test_rejects_bundle_escape(tmp_path: Path, field: str, value: str) -> None:
    folder = bundle(tmp_path)
    manifest = json.loads((folder / "program.json").read_text())
    manifest["courses"][0]["lab_files"][0][field] = value
    (folder / "program.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        prepare(tmp_path, "test")


async def test_missing_environment_and_duplicate_start(tmp_path: Path) -> None:
    bundle(tmp_path)
    lab = NotebookLab(Settings(_env_file=None))  # type: ignore[call-arg]
    lab.root = tmp_path
    lab.start("test", False)
    task = lab.task
    lab.start("other", True)
    assert lab.task is task
    assert task
    await task
    assert lab.status == "needs_install"
    assert lab.course_id == "test"
    assert lab.process is None
    await lab.close()


async def test_rejects_external_origin_and_missing_action_header() -> None:
    app = create_app(Settings(auto_migrate=False, _env_file=None))  # type: ignore[call-arg]
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/notebooks/start",
            json={"course_id": "test"},
            headers={"Origin": "https://example.com", "X-Notebook-Action": "start"},
        )
        assert response.status_code == 403
        response = await client.post("/api/notebooks/start", json={"course_id": "test"})
        assert response.status_code == 403
        response = await client.get("/api/notebooks/status")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert app.state.notebook_lab.task is None


async def test_shutdown_cancels_pending_setup(tmp_path: Path) -> None:
    lab = NotebookLab(Settings(_env_file=None))  # type: ignore[call-arg]
    lab.task = asyncio.create_task(asyncio.sleep(60))
    await lab.close()
    assert lab.task.cancelled()


def test_failed_copy_is_retryable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import shutil

    bundle(tmp_path)
    original = shutil.copyfileobj

    def fail(source: object, target: object) -> None:
        raise OSError("Disk full")

    monkeypatch.setattr(shutil, "copyfileobj", fail)
    with pytest.raises(OSError):
        prepare(tmp_path, "test")
    assert not (tmp_path / "data/notebooks/test/task.ipynb").exists()
    assert not list((tmp_path / "data/notebooks/test").glob(".preparing-*"))
    monkeypatch.setattr(shutil, "copyfileobj", original)
    prepare(tmp_path, "test")
    assert (tmp_path / "data/notebooks/test/task.ipynb").read_text().startswith('{"nbformat"')


async def test_incomplete_environment_offers_repair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle(tmp_path)
    python = tmp_path / "data/notebook-env/bin/python"
    python.parent.mkdir(parents=True)
    python.touch()
    lab = NotebookLab(Settings(_env_file=None))  # type: ignore[call-arg]
    lab.root = tmp_path

    async def fail(args: list[str]) -> None:
        raise ValueError("Installation failed")

    monkeypatch.setattr(lab, "command", fail)
    lab.start("test", True)
    assert lab.task
    await lab.task
    assert lab.status == "needs_install"
    lab.start("test", False)
    assert lab.task
    await lab.task
    assert lab.status == "needs_install"
    assert lab.process is None


async def test_launched_lab_resolves_environment_pip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import hmac

    import httpx

    bundle(tmp_path)
    bindir = tmp_path / "data/notebook-env/bin"
    bindir.mkdir(parents=True)
    for name in ("python", "pip"):
        tool = bindir / name
        tool.write_text("#!/bin/sh\nexit 0\n")
        tool.chmod(0o755)
    monkeypatch.setenv("PATH", os.defpath)
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-secret")
    lab = NotebookLab(Settings(_env_file=None))  # type: ignore[call-arg]
    lab.root = tmp_path
    launches: list[dict[str, str]] = []

    class Process:
        pid = 1071
        returncode: int | None = None

        def terminate(self) -> None:
            self.returncode = 0

        async def wait(self) -> int:
            return 0

    async def launch(*args: object, **kwargs: object) -> Process:
        env = kwargs["env"]
        assert isinstance(env, dict)
        launches.append(env)
        (Path(env["JUPYTER_RUNTIME_DIR"]) / "jpserver-1071.json").write_text(
            json.dumps(
                {
                    "pid": 1071,
                    "port": lab.port,
                    "hostname": "127.0.0.1",
                    "root_dir": str(lab.root / "data/notebooks"),
                    "token": env["JUPYTER_TOKEN"],
                }
            )
        )
        return Process()

    async def ready(args: list[str]) -> None:
        pass

    original_client = httpx.AsyncClient

    def prove(request: httpx.Request) -> httpx.Response:
        assert "authorization" not in request.headers and "token" not in str(request.url)
        challenge = request.url.path.rsplit("/", 1)[1]
        signature = hmac.digest(
            bytes.fromhex(launches[0]["AUDHS_NOTEBOOK_PROOF_KEY"]), challenge.encode(), "sha256"
        )
        return httpx.Response(204, headers={"X-AuDHS-Listener-Proof": signature.hex()})

    transport = httpx.MockTransport(prove)
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original_client(transport=transport))
    monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)
    monkeypatch.setattr(lab, "command", ready)
    lab.start("test", False)
    assert lab.task
    await lab.task
    assert lab.status == "ready"
    assert shutil.which("pip", path=launches[0]["PATH"]) == str(bindir / "pip")
    assert launches[0]["VIRTUAL_ENV"] == str(bindir.parent)
    assert "OPENAI_API_KEY" not in launches[0]
    await lab.close()


@pytest.mark.parametrize("status", [200, 204])
async def test_occupied_port_cannot_claim_readiness_or_receive_login_token(
    tmp_path, monkeypatch, status
):
    import httpx

    bundle(tmp_path)
    lab = NotebookLab(Settings(_env_file=None))
    lab.root = tmp_path
    env_python = (
        tmp_path / "data/notebook-env" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    )
    env_python.parent.mkdir(parents=True)
    env_python.touch()
    seen = []

    class Process:
        pid = 1075
        returncode = None

    proc = Process()

    async def launch(*args, **kwargs):
        env = kwargs["env"]
        # Even a genuine server-info record can precede Jupyter's async socket bind.
        (Path(env["JUPYTER_RUNTIME_DIR"]) / "jpserver-1075.json").write_text(
            json.dumps(
                {
                    "pid": proc.pid,
                    "port": lab.port,
                    "hostname": "127.0.0.1",
                    "root_dir": str(tmp_path / "data/notebooks"),
                    "token": env["JUPYTER_TOKEN"],
                }
            )
        )
        return proc

    async def installed(_args):
        pass

    def wrong_listener(request):
        seen.append(request)
        proc.returncode = 1
        return httpx.Response(status, headers={"X-AuDHS-Listener-Proof": "0" * 64})

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(wrong_listener)),
    )
    monkeypatch.setattr(lab, "command", installed)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)
    try:
        lab.start_command(lab.service_id, "one", "test", False)
        await lab.task
        assert lab.snapshot()["status"] == "error" and lab.snapshot()["url"] is None
        assert len(seen) == 1
        assert "authorization" not in seen[0].headers and lab.token not in str(seen[0].url)
        assert lab.token not in repr(
            list(seen[0].headers.items())
        ) and lab.proof_key.hex() not in str(seen[0].url)
    finally:
        await lab.close()


@pytest.mark.skipif(__import__("os").name != "posix", reason="Uses POSIX signal handling")
async def test_shutdown_reaps_installer_that_ignores_termination(tmp_path: Path) -> None:
    import sys

    ready = tmp_path / "installer-ready"
    lab = NotebookLab(Settings(_env_file=None))  # type: ignore[call-arg]
    lab.task = asyncio.create_task(
        lab.command(
            [
                sys.executable,
                "-c",
                "import pathlib,signal,sys,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);"
                "pathlib.Path(sys.argv[1]).touch();time.sleep(30)",
                str(ready),
            ]
        )
    )
    try:
        async with asyncio.timeout(10):
            while not ready.exists():  # noqa: ASYNC110 - sentinel from the child process
                await asyncio.sleep(0.02)
        child = lab.installer
        assert child is not None
        await asyncio.wait_for(lab.close(), 10)
        assert child.returncode is not None and lab.installer is None
    finally:
        if lab.installer and lab.installer.returncode is None:
            lab.installer.kill()
            await lab.installer.wait()
