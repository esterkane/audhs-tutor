"""Explicit, local-only notebook preparation. Never executes notebook cells."""

import asyncio
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import tempfile
import urllib.parse
import uuid
from pathlib import Path

import httpx

from app.core.config import Settings
from app.core.errors import AppError

PACKAGES = [
    "pip==26.2.1",
    "jupyterlab==4.6.4",
    "ipykernel==7.4.0",
    "numpy==2.5.3",
    "pandas==3.0.6",
    "matplotlib==3.11.2",
    "scikit-learn==1.9.1",
]


def copy_once(src: Path, target: Path, *, verified: bytes | None = None) -> None:
    # Keep existing learner edits; reopening is never a reset.
    if not target.exists():
        staging: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=target.parent, prefix=".preparing-", delete=False
            ) as stream:
                staging = Path(stream.name)
                if verified is None:
                    with src.open("rb") as original:
                        shutil.copyfileobj(original, stream)
                else:
                    stream.write(verified)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(staging, target)  # Atomic publish without replacing learner work.
            except FileExistsError:
                pass
        finally:
            if staging is not None:
                staging.unlink(missing_ok=True)


def prepare(root: Path, course_id: str) -> str:
    source = root / "frontend/public/local-learning"
    manifest = json.loads((source / "program.json").read_text())
    course = next((c for c in manifest["courses"] if c["id"] == course_id), None)
    if course is None or not isinstance(course.get("lab_files"), list):
        raise ValueError("This course has no configured local notebook bundle yet.")
    if not course_id or any(
        c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
        for c in course_id
    ):
        raise ValueError("Invalid course identifier.")
    folder = root / "data/notebooks" / course_id
    if folder.is_symlink():
        raise ValueError("Notebook folder cannot be a symlink.")
    folder.mkdir(parents=True, exist_ok=True)
    if not folder.resolve().is_relative_to((root / "data/notebooks").resolve()):
        raise ValueError("Invalid notebook folder.")
    notebook = ""
    for item in course["lab_files"]:
        src_name, name = item["source"], item["name"]
        if (
            not isinstance(src_name, str)
            or not isinstance(name, str)
            or Path(name).name != name
            or name in {".", ".."}
        ):
            raise ValueError("Invalid bundle filename.")
        src = (source / src_name).resolve()
        if not src.is_relative_to(source.resolve()) or not src.is_file():
            raise ValueError("A configured notebook file is missing or outside local materials.")
        target = folder / name
        if target.is_symlink():
            raise ValueError("Notebook files cannot be symlinks.")
        copy_once(src, target)
        if name.endswith(".ipynb") and not notebook:
            notebook = name
    if not notebook:
        raise ValueError("The bundle has no notebook.")
    return f"{course_id}/{notebook}"


def prepare_upload(root: Path, course_id: str, source: Path) -> str:
    # Only the server constructs this identity and resolves the content-addressed source.
    if not re.fullmatch(r"upload-[0-7][0-9A-HJKMNP-TV-Z]{25}", course_id):
        raise ValueError("Invalid notebook identifier.")
    folder = root / "data/notebooks" / course_id
    target = folder / "notebook.ipynb"
    if target.resolve() != root.resolve() / target.relative_to(root) or target.is_symlink():
        raise ValueError("Notebook working files cannot be symlinks.")
    if target.exists() and not target.is_file():
        raise ValueError("Notebook working copy must be a regular file.")
    folder.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        raw = source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != source.stem:
            raise ValueError("The uploaded original no longer matches the saved source.")
        notebook = json.loads(raw)
        if (
            not isinstance(notebook, dict)
            or notebook.get("nbformat") != 4
            or not isinstance(notebook.get("cells"), list)
        ):
            raise ValueError("Open a version 4 Jupyter notebook.")
        copy_once(source, target, verified=raw)
    return f"{course_id}/notebook.ipynb"


class NotebookLab:
    def __init__(self, settings: Settings) -> None:
        self.root = settings.project_root
        self.port = settings.notebook_lab_port
        self.status = "idle"
        self.message = "Prepare the notebook and open a local scientific Python workspace."
        self.url: str | None = None
        self.task: asyncio.Task[None] | None = None
        self.process: asyncio.subprocess.Process | None = None
        self.installer: asyncio.subprocess.Process | None = None
        self.token = ""
        self.proof_key = b""
        self.runtime: tempfile.TemporaryDirectory[str] | None = None
        self.targets: dict[str, tuple[asyncio.subprocess.Process, str]] = {}
        self.course_id = ""
        self.service_id = str(uuid.uuid4())
        self.command_id: str | None = None
        self.commands: dict[str, tuple[tuple[str, bool], dict[str, str | None]]] = {}
        self.env = {
            k: v
            for k, v in os.environ.items()
            if not any(s in k.upper() for s in ("KEY", "TOKEN", "SECRET", "PASSWORD"))
        }

    def snapshot(self) -> dict[str, str | None]:
        if self.status == "ready" and self.process and self.process.returncode is not None:
            self.status, self.url, self.message = (
                "error",
                None,
                "The notebook lab stopped. Open it again.",
            )
        return {
            "status": self.status,
            "message": self.message,
            "url": self.url,
            "course_id": self.course_id,
            "service_id": self.service_id,
            "request_id": self.command_id,
        }

    def lookup(self, service_id: str, request_id: str) -> dict[str, str | None]:
        if service_id != self.service_id or request_id not in self.commands:
            raise AppError(
                "notebook_outcome_unknown",
                "This setup request is not known by the current backend. Do not automatically restart it.",
                409,
            )
        if request_id == self.command_id:
            return self.snapshot()
        saved = dict(self.commands[request_id][1])
        if saved["status"] == "ready" and (
            request_id not in self.targets or not self._live(self.targets[request_id][0])
        ):
            return {
                **saved,
                "status": "error",
                "url": None,
                "message": "The notebook lab stopped. Your prepared files are kept.",
            }
        return saved

    def _live(self, process: asyncio.subprocess.Process) -> bool:
        return self.process is process and process.returncode is None

    def _owns_record(self, process: asyncio.subprocess.Process) -> bool:
        if self.runtime is None or not self._live(process):
            return False
        record = Path(self.runtime.name) / f"jpserver-{process.pid}.json"
        try:
            info = json.loads(record.read_bytes())
            return (
                isinstance(info, dict)
                and info.get("pid") == process.pid
                and info.get("port") == self.port
                and info.get("hostname") == "127.0.0.1"
                and isinstance(info.get("root_dir"), str)
                and Path(info["root_dir"]) == (self.root / "data/notebooks").absolute()
                and isinstance(info.get("token"), str)
                and secrets.compare_digest(info["token"], self.token)
            )
        except (OSError, ValueError, TypeError):
            return False

    async def _verified_listener(
        self, client: httpx.AsyncClient, process: asyncio.subprocess.Process
    ) -> bool:
        if not self._owns_record(process):
            return False
        challenge = secrets.token_hex(32)
        expected = hmac.digest(self.proof_key, challenge.encode("ascii"), "sha256").hex()
        try:
            async with client.stream(
                "GET", f"http://127.0.0.1:{self.port}/audhs-listener-proof/{challenge}"
            ) as response:
                return (
                    response.status_code == 204
                    and secrets.compare_digest(
                        response.headers.get("X-AuDHS-Listener-Proof", ""), expected
                    )
                    and self._live(process)
                )
        except (httpx.HTTPError, TypeError):
            return False

    async def launch_url(self, service_id: str, request_id: str) -> str:
        target = self.targets.get(request_id)
        if service_id == self.service_id and target is not None:
            process, notebook = target
            async with httpx.AsyncClient(timeout=2, trust_env=False) as client:
                if await self._verified_listener(client, process):
                    return f"http://127.0.0.1:{self.port}/lab/tree/{urllib.parse.quote(notebook)}?token={self.token}"
        raise AppError(
            "notebook_listener_unavailable", "The notebook lab stopped. Open it again.", 409
        )

    def start_command(
        self,
        service_id: str,
        request_id: str,
        course_id: str,
        install: bool,
        *,
        upload: Path | None = None,
    ) -> dict[str, str | None]:
        if service_id != self.service_id:
            raise AppError(
                "notebook_outcome_unknown",
                "The notebook backend restarted. Check setup status before starting again.",
                409,
            )
        previous = self.commands.get(request_id)
        if previous is not None:
            if previous[0] != (course_id, install):
                raise AppError(
                    "notebook_request_conflict",
                    "This request already belongs to different setup options.",
                    409,
                )
            return self.lookup(service_id, request_id)
        if self.task and not self.task.done():
            raise AppError(
                "notebook_busy",
                "Another notebook setup is running. Check its status before starting this one.",
                409,
            )
        # Never evict identities and accidentally permit an old request to run again.
        if len(self.commands) >= 128:
            raise AppError(
                "notebook_receipts_full",
                "Setup history is full for this backend instance. Existing requests can still be checked.",
                409,
            )
        self.start(course_id, install, upload=upload)
        self.command_id = request_id
        self.commands[request_id] = ((course_id, install), self.snapshot())
        return self.snapshot()

    def start(self, course_id: str, install: bool, *, upload: Path | None = None) -> None:
        if self.task and not self.task.done():
            return
        if self.command_id is not None:
            payload, _ = self.commands[self.command_id]
            self.commands[self.command_id] = (payload, self.snapshot())
        self.command_id = None
        self.course_id = course_id
        self.url = None
        self.status = "preparing"
        self.message = "Preparing local files; existing edits will be preserved."
        self.task = asyncio.create_task(
            self._start(course_id, install)
            if upload is None
            else self._start(course_id, install, upload)
        )

    async def command(self, args: list[str]) -> None:
        self.installer = await asyncio.create_subprocess_exec(
            *args,
            env=self.env,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            code = await asyncio.wait_for(self.installer.wait(), 600)
            if code:
                raise ValueError(
                    "Notebook environment setup failed. Check network access and retry setup."
                )
        finally:
            if self.installer.returncode is None:
                self.installer.terminate()
                await self.installer.wait()
            self.installer = None

    async def _start(self, course_id: str, install: bool, upload: Path | None = None) -> None:
        try:
            notebook = (
                await asyncio.to_thread(prepare, self.root, course_id)
                if upload is None
                else await asyncio.to_thread(prepare_upload, self.root, course_id, upload)
            )
            environment = self.root / "data/notebook-env"
            python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            if install:
                self.status, self.message = (
                    "installing",
                    "Installing the pinned scientific Python environment. This may take several minutes.",
                )
                if not python.exists():
                    await self.command(
                        ["uv", "venv", "--python", "3.12", str(python.parent.parent)]
                    )
                await self.command(["uv", "pip", "install", "--python", str(python), *PACKAGES])
            if not python.exists():
                self.status, self.message = (
                    "needs_install",
                    "Install the local notebook tools once, then open your prepared notebook.",
                )
                return
            try:
                await self.command(
                    [
                        str(python),
                        "-c",
                        "import pip, jupyterlab, ipykernel, numpy, pandas, matplotlib, sklearn",
                    ]
                )
            except ValueError:
                self.status, self.message = (
                    "needs_install",
                    "Notebook tools are incomplete. Install or repair the local environment.",
                )
                return
            self.status, self.message = (
                "starting",
                "Starting authenticated Jupyter on this computer…",
            )
            starting_new_process = self.process is None or self.process.returncode is not None
            if starting_new_process:
                if self.runtime:
                    self.runtime.cleanup()
                self.runtime = tempfile.TemporaryDirectory(prefix="audhs-jupyter-")
                self.targets.clear()
                self.token = secrets.token_urlsafe(32)
                self.proof_key = secrets.token_bytes(32)
                self.process = await asyncio.create_subprocess_exec(
                    str(python),
                    "-I",
                    str(Path(__file__).with_name("serve.py")),
                    "--no-browser",
                    "--ServerApp.ip=127.0.0.1",
                    f"--ServerApp.port={self.port}",
                    "--ServerApp.port_retries=0",
                    f"--ServerApp.root_dir={self.root / 'data/notebooks'}",
                    env={
                        **self.env,
                        "PATH": str(python.parent) + os.pathsep + self.env.get("PATH", os.defpath),
                        "VIRTUAL_ENV": str(python.parent.parent),
                        "JUPYTER_TOKEN": self.token,
                        "JUPYTER_RUNTIME_DIR": self.runtime.name,
                        "AUDHS_NOTEBOOK_PROOF_KEY": self.proof_key.hex(),
                    },
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
            assert self.process is not None
            async with httpx.AsyncClient(timeout=2, trust_env=False) as client:
                for _ in range(60):
                    if self.process.returncode is not None:
                        raise ValueError(
                            f"Jupyter could not start on port {self.port}. "
                            "If it is busy, change NOTEBOOK_LAB_PORT and restart the tutor."
                        )
                    if await self._verified_listener(client, self.process):
                        request = self.command_id or str(uuid.uuid4())
                        self.targets[request] = (self.process, notebook)
                        self.url = f"/api/notebooks/open/{self.service_id}/{request}"
                        self.status, self.message = (
                            "ready",
                            "Files are ready. Open the lab, read the instructions, then run cells yourself.",
                        )
                        return
                    await asyncio.sleep(0.5)
            if starting_new_process:
                await self._stop_owned_process()
            raise ValueError("Jupyter did not become ready. Retry opening the lab.")
        except (TimeoutError, ValueError, OSError, KeyError, TypeError) as exc:
            self.status = "needs_install" if self.status == "installing" else "error"
            self.message = (
                str(exc)
                if isinstance(exc, ValueError)
                else "Could not prepare the local notebook environment. Check local files and retry."
            )

    async def close(self) -> None:
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        await self._stop_owned_process()

    async def _stop_owned_process(self) -> None:
        if self.process and self.process.returncode is None:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), 5)
            except TimeoutError:
                self.process.kill()
                await self.process.wait()
        if self.runtime:
            self.runtime.cleanup()
            self.runtime = None
        self.targets.clear()
