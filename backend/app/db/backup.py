"""Versioned, integrity-checked backup of one installation; restore into an **empty** target.

P5 `backup-restore`. This is the recovery path (`portability.py` exports one learner's rows for
portability; it is not a restore system). Principles adapted from the donor
`lernapp-updates/backend/app/services/transfer.py` (rev 8b27582: known-tables-only, empty-target
rule, staged materialisation, rollback); no code copied — the donor is PostgreSQL + Fernet.

Archive = one zip:
  manifest.json           format, version, scope, created_at, app revision, tables, index metadata,
                          reconstruction config (no secrets), source references, files + sha256
  manifest.sha256         hash of manifest.json
  db/tutor.sqlite3        consistent snapshot (sqlite3 online-backup API; WAL folded; VACUUMed)
  transcripts/<sha>.json  STT cache (optional)

Excluded by design: `.env` / any secret (`anthropic_api_key`, `hf_token`), model binaries
(`data/models`), the Qdrant storage (rebuildable: `scripts/reindex.py`, the manifest records the
collection/embedding metadata), course originals (referenced by uri + content hash, never copied).

Scopes: `learner` (default) drops the corpus tables — `chunk`, `chunk_provenance`, `index_state` —
and the session checkpoints (they embed retrieved passages), keeping documents/versions as source
references; assessment items and cached representations derived from the material stay (they may
quote short passages). `full` keeps everything for private recovery (purchased course text stays
inside; policy decision recorded in docs/IMPROVEMENT-PLAN.md).

Not encrypted: `cryptography` is not an approved dependency. The manifest says `"encryption":
"none"`; the sha256 list is integrity, not authentication. Treat the file like the database itself.

Restore never touches a live installation: the target must not exist or must be an empty directory,
members are streamed to a staging directory next to it (names validated against a closed list,
never `extractall`, symlinks refused, sizes bounded by the manifest), the snapshot is
integrity-checked, its Alembic revision must be one this code knows, migrations are applied inside
the staging copy, and only then is the staging directory renamed into place. Any failure removes
the staging directory and leaves the target untouched.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import stat
import tempfile
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit, urlunsplit

from alembic.script import ScriptDirectory
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.db import backup_crypto
from app.db import models as _models  # noqa: F401  (registers every table on Base.metadata)
from app.db.base import Base
from app.db.ddl import LEARNING_EVENT_GUARDS
from app.db.migrate import alembic_config, upgrade_to_head

FORMAT = "audhs-tutor-backup"
VERSION = 1
SCOPES = ("learner", "full")
DB_MEMBER = "db/tutor.sqlite3"
MANIFEST = "manifest.json"
MANIFEST_SUM = "manifest.sha256"
# learner scope removes the corpus tables *and* the session checkpoints (resume state, 7-day TTL,
# which embed retrieved passages). Derived learner artefacts — assessment items cut from lectures,
# cached representations — may still quote short passages; the manifest says so.
CORPUS_TEXT_TABLES = ("chunk_provenance", "chunk", "index_state", "session_checkpoint")
EXCLUDED_SETTINGS = ("anthropic_api_key", "openai_api_key", "hf_token")
RECONSTRUCTION_SETTINGS = (
    "app_env",
    "routing_profile",
    "embed_model",
    "ollama_host",
    "qdrant_url",
    "kokoro_url",
    "retrieval_max_per_document",
    "quarantine_below_trust",
    "ingest_roots",
    "transcript_cache_dir",
    "vision_cache_dir",
    "stt_language",
    "models_dir",
    "daily_budget_usd",
)
_TRANSCRIPT_MEMBER = re.compile(r"^transcripts/[0-9a-f]{16,64}\.json$")
_URL_SETTINGS = ("ollama_host", "qdrant_url", "kokoro_url")
MAX_MEMBERS = 20_000
ENCRYPTION_LABEL = "aes-256-gcm+scrypt envelope v1 (see backup_crypto)"
MAX_TOTAL_BYTES = 16 * 1024**3
_CHUNK = 1 << 20


class BackupError(ValueError):
    """Refused backup/restore; the message is safe to show. Nothing was changed."""


class FileEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size: int = Field(ge=0)


class CollectionEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    collection: str = ""
    embedding_registry_id: str = ""
    embedding_version: int = 1
    dims: int = 0
    chunk_count: int = 0
    last_reindex: str | None = None


class AppInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    alembic_revision: str | None = None
    alembic_head: str | None = None


class IndexInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    collections: list[CollectionEntry] = Field(default_factory=list)
    recovery: str = ""


class SourcesInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    note: str = ""
    documents: list[dict[str, Any]] = Field(default_factory=list)


class ManifestV1(BaseModel):
    """The only manifest shape this build reads; unknown keys are ignored, wrong shapes refused."""

    model_config = ConfigDict(extra="ignore")
    format: Literal["audhs-tutor-backup"]
    version: Literal[1]
    purpose: str = "private-recovery"
    scope: Literal["learner", "full"]
    created_at: str = ""
    encryption: str = "none"
    app: AppInfo = Field(default_factory=AppInfo)
    database: dict[str, Any] = Field(default_factory=dict)
    index: IndexInfo = Field(default_factory=IndexInfo)
    config: dict[str, Any] = Field(default_factory=dict)
    sources: SourcesInfo = Field(default_factory=SourcesInfo)
    excluded: list[str] = Field(default_factory=list)
    files: list[FileEntry] = Field(min_length=1)


@dataclass
class Report:
    path: Path
    manifest: dict[str, Any]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(_CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def _utc() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _db_path(sync_url: str) -> Path:
    if not sync_url.startswith("sqlite:///"):
        raise BackupError("only SQLite databases are backed up in Phase 1")
    return Path(sync_url.removeprefix("sqlite:///"))


def known_revisions() -> set[str]:
    script = ScriptDirectory.from_config(alembic_config("sqlite://"))
    return {rev.revision for rev in script.walk_revisions()}


def head_revision() -> str | None:
    script = ScriptDirectory.from_config(alembic_config("sqlite://"))
    return script.get_current_head()


# ----------------------------------------------------------------------------- create
def _snapshot(src_path: Path, dst_path: Path, *, scope: str) -> dict[str, Any]:
    """Consistent copy via the online-backup API; corpus text removed for `learner` scope."""
    if not src_path.is_file():
        raise BackupError(f"database not found: {src_path}")
    try:
        src = sqlite3.connect(f"{src_path.resolve().as_uri()}?mode=ro", uri=True)
    except sqlite3.Error as e:
        raise BackupError(f"cannot open {src_path}: {e}") from e
    dst = sqlite3.connect(dst_path)
    try:
        src.backup(dst)
    except sqlite3.Error as e:
        raise BackupError(f"cannot snapshot {src_path}: {e}") from e
    finally:
        src.close()
    try:
        if not _has_table(dst, "alembic_version"):
            raise BackupError("the database has no schema revision (not created by migrations)")
        rev = dst.execute("SELECT version_num FROM alembic_version").fetchone()
        if not rev or rev[0] != head_revision():
            raise BackupError(
                f"the database is at schema revision {rev[0] if rev else None!r}, this build's "
                f"head is {head_revision()!r}: run `make migrate-apply` first"
            )
        dst.row_factory = sqlite3.Row
        index_rows = (
            [
                dict(r)
                for r in dst.execute(
                    "SELECT collection, embedding_registry_id, embedding_version, dims, chunk_count, "
                    "last_reindex FROM index_state"
                )
            ]
            if _has_table(dst, "index_state")
            else []
        )
        sources = (
            [
                dict(r)
                for r in dst.execute(
                    "SELECT d.id AS document_id, d.uri, d.course, d.section, d.lecture, d.title, "
                    "d.source_type, (SELECT content_hash FROM document_version v "
                    "WHERE v.document_id = d.id ORDER BY v.version DESC LIMIT 1) AS content_hash "
                    "FROM document d ORDER BY d.course, d.section, d.lecture, d.title"
                )
            ]
            if _has_table(dst, "document")
            else []
        )
        if scope == "learner":
            for table in CORPUS_TEXT_TABLES:
                if _has_table(dst, table):
                    dst.execute(f'DELETE FROM "{table}"')
            dst.commit()
        revision = rev
        tables = {
            str(r[0]): int(dst.execute(f'SELECT count(*) FROM "{r[0]}"').fetchone()[0])
            for r in dst.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name"
            ).fetchall()
        }
        dst.execute("PRAGMA journal_mode=DELETE")  # one file, no -wal sidecar
        dst.commit()
        dst.execute("VACUUM")
    finally:
        dst.close()
    return {
        "alembic_revision": str(revision[0]) if revision else None,
        "tables": tables,
        "index": index_rows,
        "sources": sources,
    }


def _strip_userinfo(url: str) -> str:
    """`http://user:pw@host:port` → `http://host:port` (never store credentials in a manifest)."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return ""
    if "@" not in parts.netloc:
        return url
    host = parts.netloc.rsplit("@", 1)[1]
    return urlunsplit((parts.scheme, host, parts.path, parts.query, parts.fragment))


def _has_table(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def create_backup(
    sync_url: str,
    out: Path,
    *,
    scope: str = "learner",
    transcripts_dir: Path | None = None,
    settings_snapshot: dict[str, Any] | None = None,
    password: str | None = None,
    kdf_n: int = backup_crypto.DEFAULT_KDF_N,
) -> Report:
    """Write `out` atomically (temp file → rename). Refuses to overwrite. Read-only on the source.
    With `password` the archive is wrapped in the authenticated envelope of `backup_crypto`
    (ADR-0012); the password is never stored anywhere."""
    if scope not in SCOPES:
        raise BackupError(f"scope must be one of {SCOPES}")
    if password is not None and not password:
        raise BackupError("the encryption password must not be empty")
    out = out.expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    try:  # reserve the name atomically: no check-then-write window
        os.close(os.open(out, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
    except FileExistsError as e:
        raise BackupError(f"refusing to overwrite {out}") from e
    staging = Path(tempfile.mkdtemp(prefix=f".{out.name}.staging-", dir=out.parent))
    tmp_zip = staging / "archive.partial"
    try:
        db_tmp = staging / "tutor.sqlite3"
        snap = _snapshot(_db_path(sync_url), db_tmp, scope=scope)
        files: list[dict[str, Any]] = [
            {"path": DB_MEMBER, "sha256": _sha256_file(db_tmp), "size": db_tmp.stat().st_size}
        ]
        transcripts: list[Path] = []
        if transcripts_dir is not None and transcripts_dir.is_dir():
            for p in sorted(transcripts_dir.glob("*.json")):
                if (
                    p.is_file()
                    and not p.is_symlink()
                    and _TRANSCRIPT_MEMBER.match(f"transcripts/{p.name}")
                ):
                    transcripts.append(p)
                    files.append(
                        {
                            "path": f"transcripts/{p.name}",
                            "sha256": _sha256_file(p),
                            "size": p.stat().st_size,
                        }
                    )
        config = {
            k: (_strip_userinfo(str(v)) if k in _URL_SETTINGS else v)
            for k, v in (settings_snapshot or {}).items()
            if k in RECONSTRUCTION_SETTINGS and k not in EXCLUDED_SETTINGS
        }
        manifest: dict[str, Any] = {
            "format": FORMAT,
            "version": VERSION,
            "purpose": "private-recovery",
            "scope": scope,
            "created_at": _utc(),
            "encryption": ENCRYPTION_LABEL if password is not None else "none",
            "app": {"alembic_revision": snap["alembic_revision"], "alembic_head": head_revision()},
            "database": {"member": DB_MEMBER, "tables": snap["tables"]},
            "index": {
                "collections": snap["index"],
                "recovery": "vectors are not backed up; run scripts/reindex.py "
                "--embedding-version <N> after restore (the collection list above says which N)",
            },
            "config": config,
            "sources": {
                "note": "course originals are not copied; re-ingest from these paths (idempotent "
                "by content hash) if the files still exist",
                "documents": snap["sources"],
            },
            "excluded": [
                ".env and every secret",
                "data/models",
                "qdrant storage",
                "originals",
                "retained voice recordings (VOICE_DIR)",
            ]
            + (
                [
                    "corpus tables (chunk, chunk_provenance, index_state) and session checkpoints; "
                    "derived learner artefacts (assessment items, cached representations) may still "
                    "quote short passages"
                ]
                if scope == "learner"
                else []
            ),
            "files": files,
        }
        manifest_bytes = json.dumps(manifest, indent=2, ensure_ascii=False, default=str).encode()
        with zipfile.ZipFile(tmp_zip, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr(MANIFEST, manifest_bytes)
            z.writestr(MANIFEST_SUM, hashlib.sha256(manifest_bytes).hexdigest() + "\n")
            z.write(db_tmp, DB_MEMBER)
            for p in transcripts:
                z.write(p, f"transcripts/{p.name}")
        if password is not None:
            tmp_enc = staging / "archive.enc.partial"
            try:
                backup_crypto.encrypt_file(tmp_zip, tmp_enc, password, kdf_n=kdf_n)
            except backup_crypto.EncryptionError as e:
                raise BackupError(str(e)) from e
            tmp_zip.unlink()
            os.replace(tmp_enc, out)
        else:
            os.replace(tmp_zip, out)
        return Report(path=out, manifest=manifest)
    except Exception:
        out.unlink(missing_ok=True)  # the reserved (empty) name
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)


# ----------------------------------------------------------------------------- inspect / validate
def _member_ok(name: str) -> bool:
    if name == DB_MEMBER:
        return True
    return bool(_TRANSCRIPT_MEMBER.match(name))


def _safe_relative(name: str) -> bool:
    if not name or name.startswith(("/", "\\")) or "\\" in name or ":" in name:
        return False
    parts = name.split("/")
    return all(p not in ("", ".", "..") for p in parts)


def _load_manifest(z: zipfile.ZipFile) -> dict[str, Any]:
    names = z.namelist()
    if len(names) > MAX_MEMBERS:
        raise BackupError("archive has too many members")
    if MANIFEST not in names or MANIFEST_SUM not in names:
        raise BackupError("not a tutor backup (manifest missing)")
    raw = z.read(MANIFEST)
    if z.read(MANIFEST_SUM).decode().strip() != hashlib.sha256(raw).hexdigest():
        raise BackupError("manifest checksum mismatch (corrupted archive)")
    try:
        manifest = json.loads(raw)
    except json.JSONDecodeError as e:
        raise BackupError("manifest is not valid JSON") from e
    if not isinstance(manifest, dict) or manifest.get("format") != FORMAT:
        raise BackupError("not a tutor backup (unknown format)")
    if manifest.get("version") != VERSION:
        raise BackupError(
            f"backup format version {manifest.get('version')!r} is not supported "
            f"(this build reads version {VERSION})"
        )
    try:
        parsed = ManifestV1.model_validate(manifest)
    except ValidationError as e:
        first = e.errors()[0]
        where = ".".join(str(x) for x in first.get("loc", ()))
        raise BackupError(f"malformed manifest at {where or 'root'}: {first.get('msg')}") from e
    manifest = parsed.model_dump()
    listed: dict[str, dict[str, Any]] = {}
    total = 0
    for f in manifest["files"]:
        path, size = f["path"], f["size"]
        if not _safe_relative(path) or not _member_ok(path):
            raise BackupError(f"refusing unexpected or unsafe path in manifest: {path!r}")
        if path in listed:
            raise BackupError(f"duplicate file entry {path}")
        listed[path] = f
        total += size
    if total > MAX_TOTAL_BYTES:
        raise BackupError("backup exceeds the size limit")
    if DB_MEMBER not in listed:
        raise BackupError("manifest has no database member")
    extra = set(names) - set(listed) - {MANIFEST, MANIFEST_SUM}
    if extra:
        raise BackupError(
            f"archive contains members not listed in the manifest: {sorted(extra)[:3]}"
        )
    missing = set(listed) - set(names)
    if missing:
        raise BackupError(f"assets listed in the manifest are missing: {sorted(missing)[:3]}")
    for info in z.infolist():
        mode = (info.external_attr >> 16) & 0o170000
        if mode == stat.S_IFLNK:
            raise BackupError(f"symbolic links are not allowed in a backup: {info.filename}")
        if info.filename in listed and info.file_size != listed[info.filename]["size"]:
            raise BackupError(f"size mismatch for {info.filename}")
    manifest["_total_bytes"] = total
    return manifest


def _verify_member(z: zipfile.ZipFile, name: str, expected_sha: str, dest: Path | None) -> None:
    """Stream one member (to `dest` when given), hashing as we go; refuses on mismatch."""
    h = hashlib.sha256()
    with z.open(name) as src:
        if dest is None:
            for block in iter(lambda: src.read(_CHUNK), b""):
                h.update(block)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("xb") as out:
                os.chmod(dest, 0o600)
                for block in iter(lambda: src.read(_CHUNK), b""):
                    h.update(block)
                    out.write(block)
    if h.hexdigest() != expected_sha:
        if dest is not None:
            dest.unlink(missing_ok=True)
        raise BackupError(f"checksum mismatch for {name} (corrupted archive)")


@contextmanager
def _plain_archive(path: Path, password: str | None, *, workdir: Path | None) -> Iterator[Path]:
    """Yield a readable plaintext zip: `path` itself, or — for an encrypted backup — a private
    decrypted copy (0600, in `workdir` or a fresh temp dir) that is removed afterwards."""
    if not backup_crypto.is_encrypted(path):
        yield path
        return
    if password is None:
        raise BackupError("this backup is encrypted: a password is required")
    own = workdir is None
    # the plaintext copy lives next to the archive (same volume, never the shared system temp)
    work = (
        Path(tempfile.mkdtemp(prefix=f".{path.name}.decrypting-", dir=path.parent))
        if workdir is None
        else workdir
    )
    plain = work / "archive.decrypted.zip"
    try:
        need = path.stat().st_size + (64 << 20)
        if shutil.disk_usage(work).free < need:
            raise BackupError("not enough free disk space to decrypt the backup next to it")
        try:
            backup_crypto.decrypt_file(path, plain, password)
        except backup_crypto.EncryptionError as e:
            raise BackupError(str(e)) from e
        except OSError as e:
            raise BackupError(f"could not write the decrypted copy: {e}") from e
        yield plain
    finally:
        plain.unlink(missing_ok=True)
        if own:
            shutil.rmtree(work, ignore_errors=True)


def inspect_backup(path: Path, password: str | None = None) -> dict[str, Any]:
    """Validate the manifest and every member's checksum. Writes nothing for a plain archive; an
    encrypted one is decrypted into a private temp file first (needs its size in free space)."""
    path = path.expanduser()
    if not path.is_file():
        raise BackupError(f"no such file: {path}")
    encrypted = backup_crypto.is_encrypted(path)
    try:
        with _plain_archive(path, password, workdir=None) as plain, zipfile.ZipFile(plain) as z:
            manifest = _load_manifest(z)
            for f in manifest["files"]:
                _verify_member(z, f["path"], f["sha256"], None)
    except zipfile.BadZipFile as e:
        raise BackupError("not a zip archive") from e
    manifest["_encrypted"] = encrypted
    return manifest


# ----------------------------------------------------------------------------- restore
def _target_is_empty(target: Path) -> bool:
    if not target.exists():
        return True
    if not target.is_dir():
        return False
    return not any(target.iterdir())


def restore_backup(path: Path, target: Path, password: str | None = None) -> Report:
    """Restore into `target` (must not exist or be an empty directory). Layout afterwards:
    `target/data/dev.db`, `target/data/transcripts/`, `target/backup-manifest.json`,
    `target/RESTORE-NOTES.md`. The live installation is never read or written."""
    path = path.expanduser()
    target = target.expanduser()
    if not path.is_file():
        raise BackupError(f"no such file: {path}")
    if not _target_is_empty(target):
        raise BackupError(
            f"refusing to restore into {target}: it is not empty. This version restores only into "
            "an empty target; point DATABASE_URL at the restored copy afterwards"
        )
    if not target.parent.is_dir():
        raise BackupError(f"parent folder does not exist: {target.parent}")
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.restoring-", dir=target.parent))
    try:
        try:
            with (
                _plain_archive(path, password, workdir=staging) as plain,
                zipfile.ZipFile(plain) as z,
            ):
                manifest = _load_manifest(z)
                revision = manifest["app"]["alembic_revision"]
                if not isinstance(revision, str) or revision not in known_revisions():
                    raise BackupError(
                        f"the snapshot's schema revision {revision!r} is unknown to this build; "
                        "restore with a build that includes it"
                    )
                free = shutil.disk_usage(target.parent).free
                if free < manifest["_total_bytes"] * 1.2 + (64 << 20):
                    raise BackupError("not enough free disk space next to the target")
                for f in manifest["files"]:
                    dest = (
                        staging / "data" / "dev.db"
                        if f["path"] == DB_MEMBER
                        else staging / "data" / f["path"]
                    )
                    _verify_member(z, f["path"], f["sha256"], dest)
        except zipfile.BadZipFile as e:
            raise BackupError("not a zip archive") from e
        db_file = staging / "data" / "dev.db"
        _check_snapshot_schema(db_file, revision)
        upgrade_to_head(f"sqlite:///{db_file}")
        _check_after_upgrade(db_file)
        manifest.pop("_total_bytes", None)
        (staging / "backup-manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False)
        )
        (staging / "RESTORE-NOTES.md").write_text(restore_notes(manifest, target))
        try:
            # rename(2) replaces an empty directory atomically; a non-empty one fails
            os.rename(staging, target)
        except OSError as e:
            raise BackupError(f"target {target} changed during the restore: {e}") from e
        return Report(path=target, manifest=manifest)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _expected_schema_objects() -> tuple[set[str], set[str]]:
    tables = set(Base.metadata.tables) | {"alembic_version"}
    triggers = set(LEARNING_EVENT_GUARDS)
    return tables, triggers


def _check_snapshot_schema(db_file: Path, revision: str) -> None:
    """Known objects only: tables this code declares (any revision so far only *adds* tables),
    indexes on those tables, exactly the append-only guard triggers, no views. A snapshot carrying
    anything else is refused before migrations run — nothing from the archive is ever executed."""
    tables, triggers = _expected_schema_objects()
    try:
        conn = sqlite3.connect(db_file)
        try:
            ok = conn.execute("PRAGMA integrity_check").fetchone()
            if not ok or ok[0] != "ok":
                raise BackupError("the database snapshot fails integrity_check")
            row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
            if not row or row[0] != revision:
                raise BackupError("the snapshot's schema revision does not match its manifest")
            objects = conn.execute(
                "SELECT type, name, tbl_name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
            ).fetchall()
        finally:
            conn.close()
    except sqlite3.DatabaseError as e:
        raise BackupError(f"the database member is not a valid SQLite file: {e}") from e
    seen_triggers: set[str] = set()
    for kind, name, tbl in objects:
        if kind == "table":
            if name not in tables:
                raise BackupError(f"snapshot contains an unknown table {name!r}")
        elif kind == "index":
            if tbl not in tables or not str(name).startswith(("ix_", "uq_")):
                raise BackupError(f"snapshot contains an unexpected index {name!r}")
        elif kind == "trigger":
            if name not in triggers:
                raise BackupError(f"snapshot contains an unexpected trigger {name!r}")
            seen_triggers.add(str(name))
        else:
            raise BackupError(f"snapshot contains an unexpected {kind} {name!r}")
    if seen_triggers != triggers:
        raise BackupError("snapshot is missing the append-only guard triggers")


def _check_after_upgrade(db_file: Path) -> None:
    conn = sqlite3.connect(db_file)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        bad = conn.execute("PRAGMA foreign_key_check").fetchall()
        if bad:
            raise BackupError(f"restored database has {len(bad)} broken foreign-key row(s)")
    finally:
        conn.close()


def restore_notes(manifest: dict[str, Any], target: Path) -> str:
    cols = manifest.get("index", {}).get("collections") or []
    versions = sorted({int(c.get("embedding_version") or 1) for c in cols}) or [1]
    lines = [
        "# Restored AuDHS-Tutor data",
        "",
        f"Backup created {manifest.get('created_at')} · scope `{manifest.get('scope')}` · schema "
        f"revision `{manifest.get('app', {}).get('alembic_revision')}` (upgraded to head here).",
        "",
        "1. Point the app at this copy: in `.env` set "
        f"`DATABASE_URL=sqlite+aiosqlite:///{(target / 'data' / 'dev.db')}` and "
        f"`TRANSCRIPT_CACHE_DIR={(target / 'data' / 'transcripts')}` (or move `data/` into the "
        "repo's `data/` folder while the app is stopped).",
        "2. Re-create secrets by hand (`ANTHROPIC_API_KEY`, `HF_TOKEN`): they are never in a backup.",
        "3. Models are not in a backup: `make models args=list` shows the registry rows; pull what "
        "you need (`scripts/models.py pull <id>`).",
        "4. Vectors are not in a backup. With Qdrant running: "
        + " ; ".join(
            f"`uv run --project backend python scripts/reindex.py --embedding-version {v}`"
            for v in versions
        )
        + ".",
    ]
    if manifest.get("scope") == "learner":
        lines.append(
            "5. Corpus tables and session checkpoints were not included (scope `learner`): "
            "re-ingest the courses listed under `sources.documents` in `backup-manifest.json` "
            "(`make ingest src=<folder>`); ingest is idempotent by content hash. Chunk ids change, "
            "so learning objects that cite the old passages will show them as 'no longer in the "
            "corpus' until re-published. Any running session was not resumed."
        )
    lines.append("")
    lines.append("Nothing outside this folder was changed by the restore.")
    return "\n".join(lines) + "\n"
