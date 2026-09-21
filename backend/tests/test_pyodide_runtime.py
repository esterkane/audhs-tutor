"""`scripts/pyodide_runtime.py` (ADR-0013): dependency resolution from a lock file, pinning through
the committed manifest, refusal of hash mismatches and version drift, offline verification.
The network is replaced by an in-memory fetcher; nothing is downloaded here."""

import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "pyodide_runtime.py"


@pytest.fixture(scope="module")
def rt() -> ModuleType:
    spec = importlib.util.spec_from_file_location("pyodide_runtime", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fake_cdn(rt: ModuleType, packages: dict[str, dict[str, object]]) -> dict[str, bytes]:
    files = {
        name: f"{name}-bytes".encode() for name in rt.CORE_FILES if name != "pyodide-lock.json"
    }
    for entry in packages.values():
        fn = str(entry["file_name"])
        files[fn] = f"{fn}-wheel".encode()
        entry["sha256"] = _sha(files[fn])
    lock = {"info": {"version": rt.VERSION}, "packages": packages}
    files["pyodide-lock.json"] = json.dumps(lock).encode()
    return files


def test_resolve_packages_follows_dependencies_and_refuses_unknown(rt: ModuleType) -> None:
    lock = {
        "packages": {
            "numpy": {"file_name": "numpy.whl", "sha256": "a" * 64, "depends": []},
            "scipy": {"file_name": "scipy.whl", "sha256": "b" * 64, "depends": ["numpy"]},
            "loop-a": {"file_name": "a.whl", "sha256": "c" * 64, "depends": ["loop-b"]},
            "loop-b": {"file_name": "b.whl", "sha256": "d" * 64, "depends": ["loop-a"]},
            "bad": {"file_name": "../evil.whl", "sha256": "e" * 64, "depends": []},
        }
    }
    assert rt.resolve_packages(lock, ("scipy",)) == [
        ("numpy.whl", "a" * 64),
        ("scipy.whl", "b" * 64),
    ]
    with pytest.raises(rt.Refusal, match="not in pyodide-lock.json"):
        rt.resolve_packages(lock, ("pandas",))
    with pytest.raises(rt.Refusal, match="dependency cycle"):
        rt.resolve_packages(lock, ("loop-a",))
    with pytest.raises(rt.Refusal, match="unsafe file name"):
        rt.resolve_packages(lock, ("bad",))


def test_install_pins_then_verifies_and_refuses_drift(rt: ModuleType, tmp_path: Path) -> None:
    packages: dict[str, dict[str, object]] = {
        "numpy": {"file_name": "numpy-2.whl", "depends": []},
    }
    cdn = _fake_cdn(rt, packages)
    fetched: list[str] = []

    def fetch(url: str) -> bytes:
        assert url.startswith(rt.INDEX_URL)
        fetched.append(url[len(rt.INDEX_URL) :])
        return cdn[url[len(rt.INDEX_URL) :]]

    dest, manifest = tmp_path / "pyodide", tmp_path / "manifest.json"
    m = rt.install(dest, ("numpy",), manifest_path=manifest, fetch=fetch, log=lambda s: None)
    assert m["version"] == rt.VERSION and set(m["files"]) == set(cdn)
    assert sorted(fetched) == sorted(cdn)
    assert json.loads(manifest.read_text())["files"]["numpy-2.whl"]["sha256"] == _sha(
        cdn["numpy-2.whl"]
    )
    assert rt.verify(dest, manifest) == []
    # a second install downloads nothing when everything matches
    fetched.clear()
    rt.install(dest, ("numpy",), manifest_path=manifest, fetch=fetch, log=lambda s: None)
    assert fetched == []
    # a damaged file is re-fetched and must match the pin; a changed upstream file is refused
    (dest / "pyodide.js").write_bytes(b"damaged")
    assert rt.verify(dest, manifest) == ["sha256 mismatch for pyodide.js"]
    rt.install(dest, ("numpy",), manifest_path=manifest, fetch=fetch, log=lambda s: None)
    assert fetched == ["pyodide.js"] and rt.verify(dest, manifest) == []
    (dest / "pyodide.asm.wasm").unlink()
    cdn["pyodide.asm.wasm"] = b"upstream changed this file"
    with pytest.raises(rt.Refusal, match="does not match the pinned"):
        rt.install(dest, ("numpy",), manifest_path=manifest, fetch=fetch, log=lambda s: None)
    assert not (dest / "pyodide.asm.wasm").exists()  # the mismatching download is not kept
    # a manifest pinning another version is refused unless the pin is refreshed on purpose
    stale = json.loads(manifest.read_text())
    stale["version"] = "0.0.1"
    manifest.write_text(json.dumps(stale))
    with pytest.raises(rt.Refusal, match="refresh-manifest"):
        rt.install(dest, ("numpy",), manifest_path=manifest, fetch=fetch, log=lambda s: None)
    assert "manifest pins '0.0.1'" in rt.verify(dest, manifest)[0]


def test_repin_never_trusts_files_already_on_disk(rt: ModuleType, tmp_path: Path) -> None:
    packages: dict[str, dict[str, object]] = {"numpy": {"file_name": "numpy-2.whl", "depends": []}}
    cdn = _fake_cdn(rt, packages)
    fetched: list[str] = []

    def fetch(url: str) -> bytes:
        fetched.append(url[len(rt.INDEX_URL) :])
        return cdn[url[len(rt.INDEX_URL) :]]

    dest = tmp_path / "pyodide"
    dest.mkdir()
    (dest / "pyodide.asm.wasm").write_bytes(b"stale core file from another release")
    m = rt.install(
        dest, ("numpy",), manifest_path=tmp_path / "m.json", fetch=fetch, log=lambda s: None
    )
    assert "pyodide.asm.wasm" in fetched  # re-fetched, not pinned from disk
    assert m["files"]["pyodide.asm.wasm"]["sha256"] == _sha(cdn["pyodide.asm.wasm"])
    assert (dest / "pyodide.asm.wasm").read_bytes() == cdn["pyodide.asm.wasm"]


def test_verify_without_manifest_or_files(rt: ModuleType, tmp_path: Path) -> None:
    assert rt.verify(tmp_path / "nowhere", tmp_path / "none.json")[0].startswith("no manifest")
    (tmp_path / "m.json").write_text(
        json.dumps({"version": rt.VERSION, "files": {"pyodide.js": {"sha256": "0" * 64}}})
    )
    assert rt.verify(tmp_path / "nowhere", tmp_path / "m.json") == ["missing pyodide.js"]
