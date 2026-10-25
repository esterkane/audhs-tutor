"""Bounded read-only notebook inventory. Never imports or executes notebook code."""

import ast
import asyncio
import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

MAX_BYTES = 10 * 1024 * 1024
# -I/-S excludes cwd, PYTHONPATH and site hooks. PathFinder locates specs only;
# no discovered module is imported and dotted parents are never resolved.
PROBE = """
import importlib.machinery, json, sys, sysconfig
from pathlib import Path
names = json.loads(sys.stdin.read())
environment = str(Path(sys.executable).parent.parent)
locations = sysconfig.get_paths('venv', vars={'base': environment, 'platbase': environment})
paths = list(dict.fromkeys([*sys.path, *(locations[key] for key in ('purelib', 'platlib'))]))
found = [name for name in names if name in sys.builtin_module_names or
    importlib.machinery.FrozenImporter.find_spec(name) is not None or
    importlib.machinery.PathFinder.find_spec(name, paths) is not None]
print(json.dumps({'found': found, 'unavailable_standard': [name for name in names
    if name not in found and name in sys.stdlib_module_names]}))
"""


class NotebookInspection(BaseModel):
    status: Literal["checked", "not_prepared", "environment_unavailable", "unavailable"]
    message: str
    code_cells: int = 0
    imports: list[str] = Field(default_factory=list)
    unavailable_imports: list[str] = Field(default_factory=list)
    unavailable_standard_imports: list[str] = Field(default_factory=list)
    local_imports: list[str] = Field(default_factory=list)
    possible_exercise_cells: list[int] = Field(default_factory=list)
    unparsed_cells: list[int] = Field(default_factory=list)
    install_cells: list[int] = Field(default_factory=list)


def inventory(root: Path, course_id: str) -> NotebookInspection:
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", course_id):
        raise ValueError("Invalid course identifier")
    manifest_file = root / "frontend/public/local-learning/program.json"
    with manifest_file.open("rb") as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError("Manifest too large")
    manifest = json.loads(raw)
    courses = manifest.get("courses") if isinstance(manifest, dict) else None
    if not isinstance(courses, list) or any(
        not isinstance(item, dict) or not isinstance(item.get("id"), str) for item in courses
    ):
        raise ValueError("Invalid course manifest")
    course = next((c for c in courses if c["id"] == course_id), None)
    if course is None:
        raise ValueError("Course unavailable")
    files = course.get("lab_files")
    if not isinstance(files, list) or any(
        not isinstance(item, dict) or not isinstance(item.get("name"), str) for item in files
    ):
        raise ValueError("Invalid notebook manifest")
    name = next((item["name"] for item in files if item["name"].endswith(".ipynb")), None)
    if name is None:
        raise ValueError("Notebook unavailable")
    if Path(name).name != name or name in {".", ".."}:
        raise ValueError("Invalid notebook name")
    parent = root / "data/notebooks" / course_id
    target = parent / name
    if any(path.is_symlink() for path in (target, parent, parent.parent)):
        raise ValueError("Unsafe notebook path")
    if not target.is_file():
        return NotebookInspection(
            status="not_prepared",
            message="Prepare this course notebook first. Existing work is never reset by this check.",
        )
    with target.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Notebook too large")
    notebook = json.loads(raw)
    cells = notebook["cells"]
    if not isinstance(cells, list) or len(cells) > 2000:
        raise ValueError("Unsupported cells")
    report = NotebookInspection(
        status="checked", message="Static check only: no cells or installation commands were run."
    )
    names: set[str] = set()
    remaining = 512 * 1024
    for index, cell in enumerate(cells, 1):
        if not isinstance(cell, dict):
            raise ValueError("Invalid cell")
        if cell.get("cell_type") != "code":
            continue
        report.code_cells += 1
        source = cell.get("source", "")
        if isinstance(source, list) and all(isinstance(line, str) for line in source):
            source = "".join(source)
        if not isinstance(source, str):
            raise ValueError("Invalid cell source")
        if re.search(r"(?im)^\s*(?:%pip|!pip|%conda|!conda)\s+install\b", source):
            report.install_cells.append(index)
        if re.search(r"(?im)^\s*#.*\b(?:TODO|FILL\s+IN|YOUR\s+CODE)\b", source):
            report.possible_exercise_cells.append(index)
        if len(source) > min(128 * 1024, remaining):
            report.unparsed_cells.append(index)
            continue
        remaining -= len(source)
        magic = any(line.lstrip().startswith(("%", "!")) for line in source.splitlines())
        if magic:
            report.unparsed_cells.append(index)
            if source.lstrip().startswith("%%"):
                continue
            source = "\n".join(
                "" if line.lstrip().startswith(("%", "!")) else line for line in source.splitlines()
            )
        try:
            tree = ast.parse(source)
        except (SyntaxError, RecursionError, ValueError):
            report.unparsed_cells.append(index)
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value is Ellipsis:
                report.possible_exercise_cells.append(index)
            if isinstance(node, ast.Import):
                names.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    report.unparsed_cells.append(index)
                elif node.module:
                    names.add(node.module.split(".")[0])
    if len(names) > 128 or any(
        not name.isascii() or not name.isidentifier() or len(name) > 80 for name in names
    ):
        raise ValueError("Import inventory too large")
    report.imports = sorted(names)
    report.local_imports = [
        name
        for name in report.imports
        if any(
            file.is_file() and not file.is_symlink() and not (parent / name).is_symlink()
            for file in (parent / f"{name}.py", parent / name / "__init__.py")
        )
    ]
    report.unparsed_cells = sorted(set(report.unparsed_cells))
    report.possible_exercise_cells = sorted(set(report.possible_exercise_cells))
    return report


async def inspect_notebook(root: Path, course_id: str, env: dict[str, str]) -> NotebookInspection:
    try:
        report = await asyncio.to_thread(inventory, root, course_id)
    except (OSError, ValueError, KeyError, TypeError, StopIteration):
        return NotebookInspection(
            status="unavailable",
            message="Could not safely inspect this prepared notebook. Check its local bundle and file format.",
        )
    if report.status != "checked":
        return report
    python = root / "data/notebook-env/bin/python"
    if not python.is_file():
        return report.model_copy(
            update={
                "status": "environment_unavailable",
                "message": (
                    "Notebook Python is not installed. Prepare or repair "
                    "the notebook environment before checking packages."
                ),
            }
        )
    process: asyncio.subprocess.Process | None = None
    try:
        process = await asyncio.create_subprocess_exec(
            str(python),
            "-I",
            "-S",
            "-B",
            "-c",
            PROBE,
            env=env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        output, _ = await asyncio.wait_for(
            process.communicate(json.dumps(report.imports).encode()), 5
        )
        if process.returncode != 0 or len(output) > 16384:
            raise ValueError("Probe failed")
        metadata = json.loads(output)
        if not isinstance(metadata, dict):
            raise ValueError("Invalid metadata")
        found = metadata.get("found")
        unavailable_standard = metadata.get("unavailable_standard")
        if not isinstance(found, list) or not isinstance(unavailable_standard, list):
            raise ValueError("Invalid metadata")
        for values in (found, unavailable_standard):
            if any(not isinstance(name, str) or name not in report.imports for name in values):
                raise ValueError("Invalid metadata")
        if set(found) & set(unavailable_standard):
            raise ValueError("Conflicting metadata")
        report.unavailable_imports = sorted(
            set(report.imports) - set(found) - set(report.local_imports)
        )
        report.unavailable_standard_imports = sorted(
            set(unavailable_standard) & set(report.unavailable_imports)
        )
        return report
    except (OSError, ValueError, TimeoutError):
        return report.model_copy(
            update={
                "status": "environment_unavailable",
                "message": "Could not check notebook Python package locations. No course code was imported or run.",
            }
        )
    finally:
        if process is not None and process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            await process.wait()
