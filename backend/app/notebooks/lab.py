"""Explicit, local-only notebook preparation. Never executes notebook cells."""

import asyncio
import json
import os
import secrets
import shutil
import tempfile
import urllib.parse
from pathlib import Path

import httpx

from app.core.config import Settings

PACKAGES = [
    "jupyterlab==4.6.4",
    "ipykernel==7.4.0",
    "numpy==2.5.3",
    "pandas==3.0.6",
    "matplotlib==3.11.2",
    "scikit-learn==1.9.1",
]


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
        # Keep existing learner edits; reopening is never a reset.
        if not target.exists():
            staging: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    dir=folder, prefix=".preparing-", delete=False
                ) as stream:
                    staging = Path(stream.name)
                    with src.open("rb") as original:
                        shutil.copyfileobj(original, stream)
                    stream.flush()
                    os.fsync(stream.fileno())
                try:
                    os.link(staging, target)  # Atomic publish without replacing learner work.
                except FileExistsError:
                    pass
            finally:
                if staging is not None:
                    staging.unlink(missing_ok=True)
        if name.endswith(".ipynb") and not notebook:
            notebook = name
    if not notebook:
        raise ValueError("The bundle has no notebook.")
    return f"{course_id}/{notebook}"


class NotebookLab:
    def __init__(self, settings: Settings) -> None:
        self.root = settings.project_root
        self.status = "idle"
        self.message = "Prepare the notebook and open a local scientific Python workspace."
        self.url: str | None = None
        self.task: asyncio.Task[None] | None = None
        self.process: asyncio.subprocess.Process | None = None
        self.installer: asyncio.subprocess.Process | None = None
        self.token = secrets.token_urlsafe(32)
        self.course_id = ""
        self.env = {
            k: v
            for k, v in os.environ.items()
            if not any(s in k.upper() for s in ("KEY", "TOKEN", "SECRET", "PASSWORD"))
        }

    def start(self, course_id: str, install: bool) -> None:
        if self.task and not self.task.done():
            return
        self.course_id = course_id
        self.url = None
        self.status = "preparing"
        self.message = "Preparing local files; existing edits will be preserved."
        self.task = asyncio.create_task(self._start(course_id, install))

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

    async def _start(self, course_id: str, install: bool) -> None:
        try:
            notebook = await asyncio.to_thread(prepare, self.root, course_id)
            python = self.root / "data/notebook-env/bin/python"
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
                        "import jupyterlab, ipykernel, numpy, pandas, matplotlib, sklearn",
                    ]
                )
            except ValueError:
                self.status, self.message = (
                    "needs_install",
                    "Notebook tools are incomplete. Install or repair the local environment.",
                )
                return
            self.status, self.message = "starting", "Starting authenticated Jupyter on this Mac…"
            if self.process is None or self.process.returncode is not None:
                self.process = await asyncio.create_subprocess_exec(
                    str(python),
                    "-m",
                    "jupyterlab",
                    "--no-browser",
                    "--ServerApp.ip=127.0.0.1",
                    "--ServerApp.port=8890",
                    "--ServerApp.port_retries=0",
                    f"--ServerApp.root_dir={self.root / 'data/notebooks'}",
                    env={**self.env, "JUPYTER_TOKEN": self.token},
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
            async with httpx.AsyncClient(timeout=2) as client:
                for _ in range(60):
                    if self.process.returncode is not None:
                        raise ValueError(
                            "Jupyter could not start. Port 8890 may be busy; use or close the existing lab."
                        )
                    try:
                        response = await client.get(
                            "http://127.0.0.1:8890/api/status",
                            headers={"Authorization": f"token {self.token}"},
                        )
                        if response.status_code == 200:
                            self.url = f"http://127.0.0.1:8890/lab/tree/{urllib.parse.quote(notebook)}?token={self.token}"
                            self.status, self.message = (
                                "ready",
                                "Files are ready. Open the lab, read the instructions, then run cells yourself.",
                            )
                            return
                    except httpx.HTTPError:
                        pass
                    await asyncio.sleep(0.5)
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
        if self.process and self.process.returncode is None:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), 5)
            except TimeoutError:
                self.process.kill()
                await self.process.wait()
