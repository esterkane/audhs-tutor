import asyncio
import json
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.notebooks import validated_source
from app.core.config import Settings
from app.db.models import Document
from app.notebooks.lab import prepare_upload


async def test_start_uploaded_notebook_without_manifest_and_reopen_edits(
    client: AsyncClient, settings: Settings, tmp_path: Path, db: AsyncSession
):
    settings.knowledge_authoring_root = str(tmp_path)
    original = json.dumps(
        {
            "nbformat": 4,
            "nbformat_minor": 5,
            "metadata": {},
            "cells": [
                {
                    "cell_type": "code",
                    "source": "6 * 7",
                    "outputs": [],
                    "metadata": {},
                    "execution_count": None,
                }
            ],
        }
    ).encode()
    upload = await client.post(
        "/api/knowledge-material/uploads", content=original, headers={"X-Filename": "source.ipynb"}
    )
    assert upload.status_code == 200, upload.text
    doc_id = upload.json()["document_id"]
    app = client._transport.app
    lab = app.state.notebook_lab
    lab.root = tmp_path
    path = f"/api/notebooks/uploads/{doc_id}"
    headers = {"host": "localhost", "X-Notebook-Action": "start"}
    assert (await client.get(path, headers=headers)).json() == {"available": True}
    command = {
        "course_id": f"upload-{doc_id}",
        "request_id": str(uuid4()),
        "service_id": lab.service_id,
    }
    assert (await client.post(path + "/start", json=command, headers=headers)).status_code == 200
    await lab.task
    assert lab.status == "needs_install" and lab.process is None
    target = tmp_path / "data/notebooks" / command["course_id"] / "notebook.ipynb"
    assert target.read_bytes() == original
    target.write_text("saved edits")
    command["request_id"] = str(uuid4())
    assert (await client.post(path + "/start", json=command, headers=headers)).status_code == 200
    await lab.task
    assert target.read_text() == "saved edits"
    document = await db.get(Document, doc_id)
    saved_source = Path(document.uri)
    assert await asyncio.to_thread(saved_source.read_bytes) == original
    await asyncio.to_thread(saved_source.write_bytes, b"truncated during storage failure")
    repaired = await client.post(
        "/api/knowledge-material/uploads", content=original, headers={"X-Filename": "source.ipynb"}
    )
    assert repaired.status_code == 200
    assert repaired.json()["document_id"] == doc_id
    assert await asyncio.to_thread(saved_source.read_bytes) == original
    assert target.read_text() == "saved edits"
    missing = str(uuid4())
    command.update(course_id="upload-" + missing, request_id=str(uuid4()))
    missing_url = "/api/notebooks/uploads/" + missing
    assert (await client.get(missing_url, headers=headers)).json() == {"available": False}
    assert (
        await client.post(missing_url + "/start", json=command, headers=headers)
    ).status_code == 404


def test_reject_other_owner_malformed_and_symlink_sources(settings: Settings, tmp_path: Path):
    settings.knowledge_authoring_root = str(tmp_path)
    owner = tmp_path / "knowledge-authoring/learner"
    owner.mkdir(parents=True)
    source = owner / ("a" * 64 + ".ipynb")
    source.write_text("source")
    assert validated_source(str(source), "different", settings) is None
    assert validated_source(str(source), "learner", settings) == source
    link = owner / ("b" * 64 + ".ipynb")
    link.symlink_to(source)
    assert validated_source(str(link), "learner", settings) is None
    invalid = owner / "not-a-content-address.ipynb"
    invalid.touch()
    assert validated_source(str(invalid), "learner", settings) is None


def test_working_copy_rejects_symlinked_data_root_and_non_file_target(tmp_path: Path):
    root = tmp_path / "project"
    external = tmp_path / "outside"
    root.mkdir()
    external.mkdir()
    data = root / "data"
    data.symlink_to(external, target_is_directory=True)
    identity = "upload-01M754WHCEMTWYHT0Q21YJNBVX"
    with pytest.raises(ValueError, match="symlinks"):
        prepare_upload(root, identity, tmp_path / "unused")
    assert not list(external.iterdir())
    data.unlink()
    (data / "notebooks" / identity / "notebook.ipynb").mkdir(parents=True)
    with pytest.raises(ValueError, match="regular file"):
        prepare_upload(root, identity, tmp_path / "unused")


async def test_rejected_output_only_notebook_leaves_no_private_upload(client, settings, tmp_path):
    settings.knowledge_authoring_root = str(tmp_path)
    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {},
        "cells": [
            {
                "cell_type": "code",
                "source": "",
                "outputs": [{"output_type": "stream", "name": "stdout", "text": "old result"}],
                "metadata": {},
                "execution_count": 3,
            }
        ],
    }
    response = await client.post(
        "/api/knowledge-material/uploads",
        content=json.dumps(notebook).encode(),
        headers={"X-Filename": "output-only.ipynb"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "empty_upload"
    assert not any(path.is_file() for path in (tmp_path / "knowledge-authoring").rglob("*"))
