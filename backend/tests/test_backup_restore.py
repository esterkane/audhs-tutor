"""P5 backup-restore: round trip of every table (learner evidence, FSRS state, preferences,
plans/checkpoints, vocabulary, curriculum, source references), scope semantics, and every refusal:
occupied target, corrupted member, incompatible version, unknown/unsafe/symlink members, missing
assets, unknown schema revision, partial failure with rollback. All on temporary databases."""

import hashlib
import io
import json
import sqlite3
import zipfile
from pathlib import Path

import pytest

from app.db import backup
from app.db.backup import BackupError, create_backup, inspect_backup, restore_backup
from app.db.migrate import upgrade_to_head
from tests._rows import dump_tables, fill_all_tables


@pytest.fixture
def source(tmp_path: Path) -> tuple[str, Path]:
    db = tmp_path / "live" / "dev.db"
    url = f"sqlite:///{db}"
    upgrade_to_head(url)
    fill_all_tables(url)
    tr = tmp_path / "live" / "transcripts"
    tr.mkdir()
    (tr / ("a" * 64 + ".json")).write_text(json.dumps({"text": "hello"}))
    (tr / "not-a-transcript.txt").write_text("ignored")
    return url, tr


def _rewrite(src: Path, dst: Path, mutate) -> None:  # type: ignore[no-untyped-def]
    """Copy a backup zip through `mutate(name, data, infos) -> list[(ZipInfo|str, bytes)]`."""
    with zipfile.ZipFile(src) as zin:
        items = [(info, zin.read(info.filename)) for info in zin.infolist()]
    with zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for info, data in mutate(items):
            zout.writestr(info, data)


def _with_manifest(items, edit):  # type: ignore[no-untyped-def]
    out = []
    for info, data in items:
        if info.filename == backup.MANIFEST:
            m = json.loads(data)
            edit(m)
            data = json.dumps(m).encode()
            out.append((info, data))
            out.append((backup.MANIFEST_SUM, (hashlib.sha256(data).hexdigest() + "\n").encode()))
        elif info.filename != backup.MANIFEST_SUM:
            out.append((info, data))
    return out


def test_round_trip_full_scope_preserves_every_table(
    tmp_path: Path, source: tuple[str, Path]
) -> None:
    url, transcripts = source
    before = dump_tables(url)
    out = tmp_path / "backups" / "full.zip"
    rep = create_backup(
        url,
        out,
        scope="full",
        transcripts_dir=transcripts,
        settings_snapshot={
            "embed_model": "nomic-embed-text",
            "anthropic_api_key": "sk-SECRET-VALUE",
            "hf_token": "hf-SECRET",
            "routing_profile": "default",
        },
    )
    m = rep.manifest
    assert m["format"] == backup.FORMAT and m["version"] == 1 and m["encryption"] == "none"
    assert m["app"]["alembic_revision"] == backup.head_revision()
    assert m["database"]["tables"]["memory_state"] == 1 and m["database"]["tables"]["chunk"] == 1
    assert m["index"]["collections"][0]["collection"].startswith("index_state")
    assert m["config"] == {"embed_model": "nomic-embed-text", "routing_profile": "default"}
    # secrets never enter the archive: check the *decompressed* manifest and every member
    with zipfile.ZipFile(out) as z:
        mj = json.loads(z.read(backup.MANIFEST))
        assert "anthropic_api_key" not in mj["config"] and "hf_token" not in mj["config"]
        assert "SECRET" not in json.dumps(mj)
        for name in z.namelist():
            assert b"SECRET" not in z.read(name), name
    assert [f["path"] for f in m["files"]] == [
        backup.DB_MEMBER,
        "transcripts/" + "a" * 64 + ".json",
    ]
    assert len(m["sources"]["documents"]) == 1 and m["sources"]["documents"][0]["uri"]
    # the source database was only read
    assert dump_tables(url) == before
    # inspect verifies every checksum; refuse to overwrite an existing archive
    assert inspect_backup(out)["scope"] == "full"
    with pytest.raises(BackupError, match="overwrite"):
        create_backup(url, out, scope="full")
    # restore into an empty target
    target = tmp_path / "restored"
    rep2 = restore_backup(out, target)
    assert rep2.path == target
    restored = f"sqlite:///{target / 'data' / 'dev.db'}"
    assert dump_tables(restored) == before  # evidence, FSRS, preferences, checkpoints, vocab, ...
    conn = sqlite3.connect(target / "data" / "dev.db")
    assert (
        conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        == backup.head_revision()
    )
    triggers = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
    assert {"learning_event_no_update", "learning_event_no_delete"} <= triggers
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    conn.close()
    assert (
        target / "data" / "transcripts" / ("a" * 64 + ".json")
    ).read_text() == '{"text": "hello"}'
    notes = (target / "RESTORE-NOTES.md").read_text()
    assert "DATABASE_URL" in notes and "reindex.py" in notes and "never in a backup" in notes
    assert json.loads((target / "backup-manifest.json").read_text())["scope"] == "full"
    assert not list(tmp_path.glob(".*restoring*"))


def test_learner_scope_drops_corpus_text_but_keeps_source_references(
    tmp_path: Path, source: tuple[str, Path]
) -> None:
    url, _ = source
    out = tmp_path / "learner.zip"
    rep = create_backup(url, out)  # default scope
    t = rep.manifest["database"]["tables"]
    assert rep.manifest["scope"] == "learner"
    assert t["chunk"] == 0 and t["chunk_provenance"] == 0 and t["index_state"] == 0
    assert t["session_checkpoint"] == 0  # resume state embeds retrieved passages
    assert t["document"] == 1 and t["document_version"] == 1 and t["learning_event"] == 1
    assert any(x.startswith("corpus tables") for x in rep.manifest["excluded"])
    # the sentinel passage text is gone from the decompressed snapshot's corpus/checkpoint tables
    with zipfile.ZipFile(out) as z:
        snap = tmp_path / "snap.sqlite3"
        snap.write_bytes(z.read(backup.DB_MEMBER))
    conn = sqlite3.connect(snap)
    for table in ("chunk", "session_checkpoint"):
        assert conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
    conn.close()
    assert rep.manifest["sources"]["documents"][0]["content_hash"]
    target = tmp_path / "restored-learner"
    restore_backup(out, target)
    restored = dump_tables(f"sqlite:///{target / 'data' / 'dev.db'}")
    before = dump_tables(url)
    assert restored["chunk"] == [] and restored["document"] == before["document"]
    assert restored["memory_state"] == before["memory_state"]
    assert "re-ingest" in (target / "RESTORE-NOTES.md").read_text()


def test_refuses_occupied_target(tmp_path: Path, source: tuple[str, Path]) -> None:
    url, _ = source
    out = tmp_path / "b.zip"
    create_backup(url, out)
    busy = tmp_path / "busy"
    busy.mkdir()
    (busy / "something.txt").write_text("mine")
    with pytest.raises(BackupError, match="not empty"):
        restore_backup(out, busy)
    assert (busy / "something.txt").read_text() == "mine"
    assert sorted(p.name for p in busy.iterdir()) == ["something.txt"]
    # an empty existing directory is fine
    empty = tmp_path / "empty"
    empty.mkdir()
    restore_backup(out, empty)
    assert (empty / "data" / "dev.db").is_file()


def test_corrupted_member_is_refused_and_leaves_no_trace(
    tmp_path: Path, source: tuple[str, Path]
) -> None:
    url, _ = source
    good = tmp_path / "good.zip"
    create_backup(url, good)
    bad = tmp_path / "bad.zip"

    def flip(items):  # type: ignore[no-untyped-def]  # noqa: E306
        out = []
        for info, data in items:
            if info.filename == backup.DB_MEMBER:
                data = data[:100] + bytes([data[100] ^ 0xFF]) + data[101:]
            out.append((info, data))
        return out

    _rewrite(good, bad, flip)
    with pytest.raises(BackupError, match="checksum mismatch"):
        inspect_backup(bad)
    target = tmp_path / "t"
    with pytest.raises(BackupError, match="checksum mismatch"):
        restore_backup(bad, target)
    assert not target.exists() and not list(tmp_path.glob(".*restoring*"))
    with pytest.raises(BackupError, match="not a zip"):
        inspect_backup(Path(__file__))

    # a member with a valid checksum that is not SQLite, and a snapshot with a foreign trigger
    def not_sqlite(items):  # type: ignore[no-untyped-def]
        junk = b"not a database at all" * 10
        return _with_manifest(
            [(i, junk if i.filename == backup.DB_MEMBER else d) for i, d in items],
            lambda m: m["files"][0].update(
                {"sha256": hashlib.sha256(junk).hexdigest(), "size": len(junk)}
            ),
        )

    _rewrite(good, tmp_path / "junk.zip", not_sqlite)
    with pytest.raises(BackupError, match="not a valid SQLite"):
        restore_backup(tmp_path / "junk.zip", tmp_path / "t2")

    def foreign_trigger(items):  # type: ignore[no-untyped-def]
        out = []
        for info, data in items:
            if info.filename == backup.DB_MEMBER:
                f = tmp_path / "evil.sqlite3"
                f.write_bytes(data)
                c = sqlite3.connect(f)
                c.execute(
                    "CREATE TRIGGER evil AFTER INSERT ON learning_event BEGIN "
                    "DELETE FROM competency_evidence; END"
                )
                c.commit()
                c.execute("PRAGMA journal_mode=DELETE")
                c.execute("VACUUM")
                c.close()
                data = f.read_bytes()
            out.append((info, data))
        return _with_manifest(
            out,
            lambda m: m["files"][0].update(
                {
                    "sha256": hashlib.sha256(
                        out[2][1] if out[2][0].filename == backup.DB_MEMBER else data
                    ).hexdigest()
                }
            ),
        )

    _rewrite(good, tmp_path / "trigger.zip", foreign_trigger)
    with pytest.raises(BackupError, match="unexpected trigger|size mismatch|checksum"):
        restore_backup(tmp_path / "trigger.zip", tmp_path / "t3")
    assert not (tmp_path / "t3").exists()


def test_incompatible_and_unsafe_archives_are_refused(
    tmp_path: Path, source: tuple[str, Path]
) -> None:
    url, _ = source
    good = tmp_path / "good.zip"
    create_backup(url, good)

    def check(name: str, mutate, match: str) -> None:  # type: ignore[no-untyped-def]
        p = tmp_path / f"{name}.zip"
        _rewrite(good, p, mutate)
        with pytest.raises(BackupError, match=match):
            restore_backup(p, tmp_path / f"t-{name}")
        assert not (tmp_path / f"t-{name}").exists()

    check(
        "version",
        lambda items: _with_manifest(items, lambda m: m.__setitem__("version", 99)),
        "not supported",
    )
    check(
        "format",
        lambda items: _with_manifest(items, lambda m: m.__setitem__("format", "other")),
        "unknown format",
    )
    check(
        "unlisted",
        lambda items: items + [(zipfile.ZipInfo("evil.py"), b"print(1)")],
        "not listed",
    )
    check(
        "traversal",
        lambda items: _with_manifest(
            items,
            lambda m: m["files"].append({"path": "../x.json", "sha256": "0" * 64, "size": 1}),
        ),
        "unsafe path",
    )
    check(
        "absolute",
        lambda items: _with_manifest(
            items,
            lambda m: m["files"].append({"path": "/etc/passwd", "sha256": "0" * 64, "size": 1}),
        ),
        "unsafe path",
    )
    check(
        "missing-asset",
        lambda items: _with_manifest(
            items,
            lambda m: m["files"].append(
                {"path": "transcripts/" + "b" * 64 + ".json", "sha256": "0" * 64, "size": 1}
            ),
        ),
        "missing",
    )
    check(
        "unknown-revision",
        lambda items: _with_manifest(
            items, lambda m: m["app"].__setitem__("alembic_revision", "deadbeefcafe")
        ),
        "unknown to this build",
    )

    def symlink(items):  # type: ignore[no-untyped-def]
        info = zipfile.ZipInfo("transcripts/" + "c" * 64 + ".json")
        info.external_attr = 0o120777 << 16
        target = b"/etc/passwd"
        sha = hashlib.sha256(target).hexdigest()
        return _with_manifest(
            items,
            lambda m: m["files"].append(
                {"path": info.filename, "sha256": sha, "size": len(target)}
            ),
        ) + [(info, target)]

    check("symlink", symlink, "symbolic links")

    # a tampered manifest with a stale checksum
    def stale(items):  # type: ignore[no-untyped-def]
        return [
            (
                info,
                data.replace(b'"scope": "learner"', b'"scope": "full"')
                if info.filename == backup.MANIFEST
                else data,
            )
            for info, data in items
        ]

    check("stale-sum", stale, "manifest checksum")


def test_partial_failure_rolls_back(
    tmp_path: Path, source: tuple[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    url, _ = source
    out = tmp_path / "b.zip"
    create_backup(url, out)

    def boom(_: str) -> None:
        raise RuntimeError("migration exploded half-way")

    monkeypatch.setattr(backup, "upgrade_to_head", boom)
    target = tmp_path / "t"
    with pytest.raises(RuntimeError):
        restore_backup(out, target)
    assert not target.exists()
    assert not list(tmp_path.glob(".*restoring*"))


def test_create_refuses_missing_db_and_non_sqlite(tmp_path: Path) -> None:
    with pytest.raises(BackupError, match="not found"):
        create_backup(f"sqlite:///{tmp_path / 'nope.db'}", tmp_path / "x.zip")
    with pytest.raises(BackupError, match="only SQLite"):
        create_backup("postgresql://x", tmp_path / "y.zip")
    assert not list(tmp_path.glob(".*"))  # no staging leftovers


def test_inspect_streams_without_writing(tmp_path: Path, source: tuple[str, Path]) -> None:
    url, transcripts = source
    out = tmp_path / "b.zip"
    create_backup(url, out, transcripts_dir=transcripts)
    before = sorted(p.name for p in tmp_path.iterdir())
    m = inspect_backup(out)
    assert m["files"][1]["path"].startswith("transcripts/")
    assert sorted(p.name for p in tmp_path.iterdir()) == before
    buf = io.BytesIO(out.read_bytes())
    assert zipfile.is_zipfile(buf)
