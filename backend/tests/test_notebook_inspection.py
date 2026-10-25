import asyncio
import json
import venv
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app
from app.notebooks import inspection


def prepared(root: Path, sources: list[str]) -> Path:
    source = root / "frontend/public/local-learning"
    source.mkdir(parents=True)
    (source / "program.json").write_text(
        json.dumps({"courses": [{"id": "test", "lab_files": [{"name": "task.ipynb"}]}]})
    )
    target = root / "data/notebooks/test/task.ipynb"
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps(
            {
                "cells": [{"cell_type": "markdown", "source": ["Instructions"]}]
                + [{"cell_type": "code", "source": [text]} for text in sources]
            }
        )
    )
    return target


def test_inventory_never_executes_and_separates_markers_and_partial_cells(tmp_path):
    sentinel = tmp_path / "EXECUTED"
    path = prepared(
        tmp_path,
        [
            f"open({str(sentinel)!r}, 'w').write('bad')\nimport json\nfrom missing_example.child import x",
            "# FILL IN your code\nx = ...",
            "%pip install example\nimport math",
            "%%bash\necho no",
            "x = (",
        ],
    )
    before = path.read_bytes()
    report = inspection.inventory(tmp_path, "test")
    assert report.code_cells == 5
    assert report.imports == ["json", "math", "missing_example"]
    assert report.possible_exercise_cells == [3]
    assert report.install_cells == [4]
    assert report.unparsed_cells == [4, 5, 6]
    assert path.read_bytes() == before and not sentinel.exists()


async def test_package_locations_found_without_importing_the_package(tmp_path):
    target = prepared(
        tmp_path, ["import json, missing_example, poisonous_example\nimport local_helper"]
    )
    env_path = tmp_path / "data/notebook-env"
    await asyncio.to_thread(venv.EnvBuilder(with_pip=False).create, env_path)
    site = next((env_path / "lib").glob("python*/site-packages"))
    sentinel = tmp_path / "PACKAGE_EXECUTED"
    (site / "poisonous_example.py").write_text(f"open({str(sentinel)!r}, 'w').write('bad')")
    (target.parent / "local_helper.py").write_text("raise RuntimeError('must not import')")
    report = await inspection.inspect_notebook(tmp_path, "test", {})
    assert report.status == "checked"
    assert report.unavailable_imports == ["missing_example"]
    assert report.local_imports == ["local_helper"]
    assert not sentinel.exists()


async def test_missing_environment_retains_static_exercise_inventory(tmp_path):
    prepared(tmp_path, ["# TODO complete earlier step\nx = ..."])
    report = await inspection.inspect_notebook(tmp_path, "test", {})
    assert report.status == "environment_unavailable"
    assert report.possible_exercise_cells == [2]


@pytest.mark.parametrize("mode", ["invalid", "large", "symlink", "course", "escape"])
async def test_invalid_inputs_are_bounded_and_do_not_expose_raw_content(
    tmp_path, monkeypatch, mode
):
    path = prepared(tmp_path, ["PRIVATE_SENTINEL"])
    course = "test"
    if mode == "invalid":
        path.write_text("PRIVATE_SENTINEL")
    elif mode == "large":
        monkeypatch.setattr(inspection, "MAX_BYTES", 8)
    elif mode == "symlink":
        path.unlink()
        path.symlink_to(tmp_path / "outside")
    elif mode == "course":
        course = "missing"
    else:
        course = "../test"
    report = await inspection.inspect_notebook(tmp_path, course, {})
    assert report.status == "unavailable"
    assert "PRIVATE_SENTINEL" not in report.model_dump_json()


async def test_missing_prepared_copy_does_not_prepare_or_start_anything(tmp_path):
    target = prepared(tmp_path, ["import json"])
    target.unlink()
    report = await inspection.inspect_notebook(tmp_path, "test", {})
    assert report.status == "not_prepared" and not target.exists()


async def test_check_endpoint_is_local_read_only_and_no_store(tmp_path):
    prepared(tmp_path, ["import json"])
    app = create_app(Settings(auto_migrate=False, _env_file=None))  # type: ignore[call-arg]
    app.state.notebook_lab.root = tmp_path
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        denied = await client.get(
            "/api/notebooks/check?course_id=test", headers={"origin": "https://outside.example"}
        )
        assert denied.status_code == 403
        response = await client.get("/api/notebooks/check?course_id=test")
        assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
        assert response.json()["status"] == "environment_unavailable"
        assert app.state.notebook_lab.task is None and app.state.notebook_lab.process is None
