import json
import os
from pathlib import Path

import pytest

from app.notebooks.edits import saved_edits


def test_saved_edits_only_return_new_source(tmp_path: Path) -> None:
    original = tmp_path / "original.ipynb"
    workspace = tmp_path / "data/notebooks/upload-test"
    workspace.mkdir(parents=True)
    copy = workspace / "notebook.ipynb"
    old = {"cell_type": "code", "source": ["1 + 2"], "outputs": []}
    original.write_text(json.dumps({"cells": [old]}))
    assert saved_edits(original, tmp_path, "test") == []
    new = {"cell_type": "markdown", "source": "My own explanation"}
    copy.write_text(json.dumps({"cells": [new, dict(old, outputs=["secret"]), new]}))
    assert saved_edits(original, tmp_path, "test") == ["My own explanation"]
    copy.unlink()
    copy.symlink_to(original)
    with pytest.raises(OSError):
        saved_edits(original, tmp_path, "test")
    copy.unlink()
    os.mkfifo(copy)
    with pytest.raises(ValueError):
        saved_edits(original, tmp_path, "test")
    copy.unlink()
    copy.write_text('{"cells":[{"cell_type":"code","source":42}]}')
    with pytest.raises(ValueError):
        saved_edits(original, tmp_path, "test")
