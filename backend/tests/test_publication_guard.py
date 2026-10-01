"""Publication inspects staged blobs, not a possibly cleaner working tree."""

import hashlib
import importlib.util
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_publication.py"
spec = importlib.util.spec_from_file_location("publication_guard", SCRIPT)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_identifier_scan_covers_comments_paths_and_case_without_logging_content() -> None:
    denied = frozenset({hashlib.sha256(b"exampleprovider").hexdigest()})
    for name, content in [
        ("api-types.ts", b"// ExampleProvider layout"),
        ("exampleprovider/parser.py", b""),
        ("source.md", b"https://EXAMPLEPROVIDER.test/course"),
        ("binary.bin", b"\0exampleprovider\xff"),
    ]:
        assert module.inspect_blob(name, content, denied) == ["prohibited source identifier"]
    assert module.inspect_blob("safe.md", b"exampleproviders and otherprovider", denied) == []


def test_staged_database_cannot_be_hidden_by_unstaged_cleanup(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    path = tmp_path / "innocent.bin"
    path.write_bytes(b"SQLite format 3\0private learner data")
    subprocess.run(["git", "add", "innocent.bin"], cwd=tmp_path, check=True)
    path.write_text("clean local copy")
    result = subprocess.run(
        ["python3", str(SCRIPT), "--repository", str(tmp_path)], capture_output=True, text=True
    )
    assert result.returncode != 0
    assert "SQLite database content" in result.stderr
    assert "private learner data" not in result.stderr
    subprocess.run(["git", "add", "innocent.bin"], cwd=tmp_path, check=True)
    assert module.check_index(tmp_path) == []


def test_private_snapshot_paths_are_forbidden_even_when_compressed() -> None:
    assert "private runtime path" in module.inspect_blob(
        "private-state/database/snapshot.gz", b"compressed"
    )
    assert "private runtime path" in module.inspect_blob(".env", b"EXAMPLE=private")
