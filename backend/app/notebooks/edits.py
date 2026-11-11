"""Compare saved cell source without running notebook code or importing cell output."""

import json
import os
import stat
from pathlib import Path

from app.knowledge.ingest.notebook import notebook_blocks

MAX_BYTES = 10 * 1024 * 1024


def _blocks(root: Path, relative: Path) -> list[str]:
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY
    directory = os.open(root, flags)
    try:
        for name in relative.parts[:-1]:
            child = os.open(name, flags, dir_fd=directory)
            os.close(directory)
            directory = child
        fd = os.open(relative.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
                raise ValueError("Invalid notebook file")
            raw = stream.read(MAX_BYTES + 1)
    finally:
        os.close(directory)
    if len(raw) > MAX_BYTES:
        raise ValueError("Notebook too large")
    notebook = json.loads(raw)
    cells = notebook.get("cells") if isinstance(notebook, dict) else None
    if not isinstance(cells, list):
        raise ValueError("Missing cells")
    sources = []
    for cell in cells:
        if not isinstance(cell, dict) or cell.get("cell_type") not in ("code", "markdown", "raw"):
            raise ValueError("Invalid cell")
        source = cell.get("source")
        if not isinstance(source, str) and not (
            isinstance(source, list) and all(isinstance(line, str) for line in source)
        ):
            raise ValueError("Invalid cell source")
        sources.append({"cell_type": cell["cell_type"], "source": source})
    return [b.text for b in notebook_blocks(json.dumps({"cells": sources}), source_only=True)]


def saved_edits(original: Path, workspace: Path, document_id: str) -> list[str]:
    known = set(_blocks(Path(original.anchor), original.relative_to(original.anchor)))
    try:
        current = _blocks(
            workspace, Path("data/notebooks") / f"upload-{document_id}" / "notebook.ipynb"
        )
    except FileNotFoundError:
        return []
    return [source for source in dict.fromkeys(current) if source not in known]
