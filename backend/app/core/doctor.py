"""Read-only readiness diagnostics. No app lifespan, credentials read, inference or repairs."""

import asyncio
import os
import sqlite3
import stat
from contextlib import closing
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel

from app.core.config import Settings

Mode = Literal["local", "authoring"]


class Check(BaseModel):
    name: str
    status: Literal["ok", "warning", "error", "skipped"]
    code: str
    detail: str


class Report(BaseModel):
    mode: Mode
    status: Literal["healthy", "degraded", "unavailable"]
    checks: list[Check]

    @property
    def exit_code(self) -> int:
        return {"healthy": 0, "degraded": 1, "unavailable": 2}[self.status]


def issue(name: str, required: bool, code: str, detail: str) -> Check:
    return Check(name=name, status="error" if required else "warning", code=code, detail=detail)


def local_url(base: str, path: str) -> str | None:
    try:
        value = urlsplit(base)
        if (
            value.scheme not in {"http", "https"}
            or value.hostname not in {"localhost", "127.0.0.1", "::1"}
            or value.username is not None
            or value.password is not None
            or value.path not in {"", "/"}
            or value.query
            or value.fragment
            or value.port is not None
            and not 0 < value.port <= 65535
        ):
            return None
    except ValueError:
        return None
    return base.rstrip("/") + path


async def service(
    client: httpx.AsyncClient, name: str, base: str, path: str, required: bool, timeout_s: float
) -> Check:
    url = local_url(base, path)
    if url is None:
        return issue(
            name,
            required,
            "unsafe_endpoint",
            "Use a plain loopback endpoint without credentials, paths or queries.",
        )

    async def probe() -> Check:
        async with client.stream("GET", url) as response:
            if response.status_code != 200:
                return issue(
                    name,
                    required,
                    "http_error",
                    "Service did not return HTTP 200; redirects are not followed.",
                )
            body = bytearray()
            async for part in response.aiter_bytes():
                body.extend(part)
                if len(body) > 65536:
                    return issue(
                        name,
                        required,
                        "response_too_large",
                        "Metadata response exceeded the diagnostic limit.",
                    )
            if name in {"api", "ollama"}:
                import json

                try:
                    data = json.loads(body)
                    valid = isinstance(data, dict) and (
                        data.get("status") == "ok" and data.get("db") == "ok"
                        if name == "api"
                        else isinstance(data.get("models"), list)
                    )
                except (ValueError, UnicodeError):
                    valid = False
                if valid and name == "ollama" and not data["models"]:
                    return issue(
                        name,
                        required,
                        "no_installed_models",
                        "Ollama is reachable but reports no installed models.",
                    )
                if not valid:
                    return issue(
                        name, required, "invalid_metadata", "Service returned unexpected metadata."
                    )
            return Check(
                name=name,
                status="ok",
                code="reachable",
                detail="Read-only metadata probe succeeded; no inference performed.",
            )

    try:
        return await asyncio.wait_for(probe(), timeout=timeout_s)
    except (httpx.HTTPError, TimeoutError, ValueError):
        return issue(
            name,
            required,
            "unreachable",
            "Service is unreachable or timed out. Start/check this local service explicitly.",
        )


def database(settings: Settings, timeout_s: float) -> Check:
    prefix = "sqlite:///"
    url = settings.sync_database_url
    if not url.startswith(prefix):
        return issue(
            "database", True, "unsupported_database", "Only local SQLite diagnostics are supported."
        )
    path = Path(url[len(prefix) :])
    if not path.is_file():
        return issue(
            "database",
            True,
            "missing_database",
            "Database file is missing; doctor does not create or migrate it.",
        )
    try:
        # mode=ro prohibits database writes; never use the application's engine/PRAGMA setup.
        with closing(
            sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=timeout_s)
        ) as connection:
            connection.execute("PRAGMA query_only=ON")
            found = connection.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' "
                "AND name IN ('learner_profile','alembic_version')"
            ).fetchone()[0]
            if found != 2:
                return issue(
                    "database",
                    True,
                    "schema_missing",
                    "Expected application schema is missing. Review migrations explicitly; doctor never applies them.",
                )
    except (sqlite3.Error, OSError, ValueError):
        return issue(
            "database",
            True,
            "unreadable_database",
            "Database could not be read; check access, file format and locks.",
        )
    return Check(
        name="database",
        status="ok",
        code="readable",
        detail="SQLite opened read-only with application tables. No integrity certification or migration performed.",
    )


def credential_storage(settings: Settings, required: bool) -> list[Check]:
    path = Path(settings.authoring_key_file)
    if not path.is_absolute():
        path = settings.project_root / path
    try:
        if any(parent.is_symlink() for parent in (path, *path.parents)):
            return [
                issue(
                    "key_storage",
                    required,
                    "unsafe_key_path",
                    "Key path contains a symlink; configure a regular private path.",
                )
            ]
        parent = path.parent
        if not parent.is_dir():
            return [
                issue(
                    "key_storage",
                    required,
                    "missing_key_directory",
                    "Private key directory is missing. Create it for the API user; doctor makes no directories.",
                )
            ]
        accessible = os.access(parent, os.W_OK | os.X_OK)
        results = [
            Check(
                name="key_storage",
                status="ok",
                code="accessible",
                detail="Directory access is available to the user running doctor; no write was attempted.",
            )
            if accessible
            else issue(
                "key_storage",
                required,
                "key_directory_unwritable",
                "Private key directory is not writable/searchable. Check ownership and access for the API user.",
            )
        ]
        if not required:
            results.append(
                Check(
                    name="authoring_key",
                    status="skipped",
                    code="optional",
                    detail="A hosted key is not required for local study; file contents were not read.",
                )
            )
        elif (
            path.is_file()
            and stat.S_ISREG(path.stat().st_mode)
            and path.stat().st_size > 0
            and os.access(path, os.R_OK)
        ):
            results.append(
                Check(
                    name="authoring_key",
                    status="ok",
                    code="present_unverified",
                    detail="Key file present and readable; contents, validity and account access are unverified.",
                )
            )
        elif settings.openai_api_key:
            results.append(
                Check(
                    name="authoring_key",
                    status="ok",
                    code="present_unverified",
                    detail="A key is configured in settings. Validity, account access and billing were not checked.",
                )
            )
        else:
            results.append(
                issue(
                    "authoring_key",
                    True,
                    "key_missing_or_unreadable",
                    "Save a key through Authoring setup. Doctor never reads or validates the credential.",
                )
            )
        return results
    except (OSError, ValueError):
        return [
            issue(
                "key_storage",
                required,
                "key_storage_unavailable",
                "Key metadata is inaccessible. Check private folder access for the API service user.",
            )
        ]


async def diagnose(
    settings: Settings,
    *,
    mode: Mode = "local",
    api_url: str = "http://127.0.0.1:8000",
    timeout_s: float = 2.0,
    transport: httpx.AsyncBaseTransport | None = None,
) -> Report:
    if not 0.1 <= timeout_s <= 10:
        raise ValueError("Diagnostic timeout must be between 0.1 and 10 seconds")
    async with httpx.AsyncClient(
        timeout=timeout_s, trust_env=False, follow_redirects=False, transport=transport
    ) as client:
        checks = list(
            await asyncio.gather(
                service(client, "api", api_url, "/api/health", True, timeout_s),
                service(
                    client, "ollama", settings.ollama_host, "/api/tags", mode == "local", timeout_s
                ),
                service(
                    client, "qdrant", settings.qdrant_url, "/readyz", mode == "local", timeout_s
                ),
            )
        )
    checks.append(await asyncio.to_thread(database, settings, timeout_s))
    checks.extend(await asyncio.to_thread(credential_storage, settings, mode == "authoring"))
    status: Literal["healthy", "degraded", "unavailable"] = (
        "unavailable"
        if any(c.status == "error" for c in checks)
        else "degraded"
        if any(c.status == "warning" for c in checks)
        else "healthy"
    )
    return Report(mode=mode, status=status, checks=checks)
