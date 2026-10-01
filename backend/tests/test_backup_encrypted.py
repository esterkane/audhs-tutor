"""ADR-0012 encrypted backups: the envelope round-trips through create → inspect → restore, refuses
a wrong password, a flipped byte anywhere, a reordered chunk, a truncated file, trailing data and
a crafted header demanding too much memory — and never stores password material. All on
temporary databases; scrypt runs with a small cost parameter here (the format is identical)."""

import base64
import json
import os
import struct
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from app.db import backup_crypto
from app.db.backup import BackupError, create_backup, inspect_backup, restore_backup
from app.db.backup_crypto import EncryptionError, decrypt_file, encrypt_file, is_encrypted
from app.db.migrate import upgrade_to_head
from tests._rows import dump_tables, fill_all_tables

KDF_N = 1 << 10  # fast for tests; production uses backup_crypto.DEFAULT_KDF_N
PW = "correct horse battery staple"


@pytest.fixture
def source(tmp_path: Path) -> str:
    db = tmp_path / "live" / "dev.db"
    url = f"sqlite:///{db}"
    upgrade_to_head(url)
    fill_all_tables(url)
    return url


def _encrypted_backup(tmp_path: Path, url: str) -> Path:
    out = tmp_path / "backups" / "full.zip.enc"
    rep = create_backup(url, out, scope="full", password=PW, kdf_n=KDF_N)
    assert rep.manifest["encryption"].startswith("aes-256-gcm+scrypt")
    return out


def test_encrypted_round_trip_and_password_required(tmp_path: Path, source: str) -> None:
    before = dump_tables(source)
    out = _encrypted_backup(tmp_path, source)
    assert is_encrypted(out) and not zipfile.is_zipfile(out)
    assert oct(out.stat().st_mode & 0o777) == "0o600"
    # the header is public but holds nothing secret
    header = backup_crypto.read_header(out)
    assert header["kdf"]["name"] == "scrypt" and header["kdf"]["n"] == KDF_N
    assert "key" not in json.dumps(header) and PW not in out.read_bytes().decode("latin-1")
    with pytest.raises(BackupError, match="encrypted: a password is required"):
        inspect_backup(out)
    m = inspect_backup(out, PW)
    assert m["_encrypted"] is True and m["database"]["tables"]["memory_state"] == 1
    target = tmp_path / "restored"
    rep = restore_backup(out, target, PW)
    assert rep.path == target
    assert dump_tables(f"sqlite:///{target / 'data' / 'dev.db'}") == before
    # the decrypted copy lived next to the archive / inside the staging dir and is gone
    assert not list(out.parent.glob(".*decrypting-*")) and not list(
        target.parent.glob(".*restoring*")
    )
    assert not list(target.rglob("archive.decrypted.zip"))
    with pytest.raises(BackupError, match="no such file"):
        restore_backup(tmp_path / "missing.enc", tmp_path / "t3", PW)


def test_wrong_password_is_refused_and_leaves_no_trace(tmp_path: Path, source: str) -> None:
    out = _encrypted_backup(tmp_path, source)
    target = tmp_path / "restored"
    with pytest.raises(BackupError, match="wrong password, or the encrypted backup is corrupted"):
        restore_backup(out, target, "not the password")
    assert not target.exists()
    assert not list(target.parent.glob(".restored.restoring-*"))
    with pytest.raises(BackupError, match="non-empty password"):
        inspect_backup(out, "")  # empty password: refused, not treated as "no password"


def _flip(path: Path, offset: int) -> Path:
    data = bytearray(path.read_bytes())
    data[offset] ^= 0x01
    bad = path.with_name(path.name + ".flipped")
    bad.write_bytes(bytes(data))
    return bad


def test_any_flipped_byte_is_refused(tmp_path: Path, source: str) -> None:
    out = _encrypted_backup(tmp_path, source)
    size = out.stat().st_size
    header_len = struct.unpack(">I", out.read_bytes()[len(backup_crypto.MAGIC) :][:4])[0]
    body_start = len(backup_crypto.MAGIC) + 4 + header_len
    for offset in (len(backup_crypto.MAGIC) + 4 + 3, body_start + 5 + 10, size - 1):
        bad = _flip(out, offset)
        with pytest.raises(BackupError):
            inspect_backup(bad, PW)


def test_truncation_reorder_and_trailing_data_are_refused(tmp_path: Path) -> None:
    plain = tmp_path / "plain.bin"
    plain.write_bytes(os.urandom(13_000))  # 4 chunks of 4096: three full, one final short
    enc = tmp_path / "plain.enc"
    encrypt_file(plain, enc, PW, kdf_n=KDF_N, chunk_size=4096)
    data = enc.read_bytes()
    header_len = struct.unpack(">I", data[len(backup_crypto.MAGIC) :][:4])[0]
    body = len(backup_crypto.MAGIC) + 4 + header_len
    hdr = struct.Struct(">IB")
    # parse chunk boundaries
    chunks = []
    pos = body
    while pos < len(data):
        ct_len, flag = hdr.unpack(data[pos : pos + hdr.size])
        chunks.append((pos, pos + hdr.size + ct_len, flag))
        pos += hdr.size + ct_len
    assert len(chunks) == 4 and chunks[-1][2] == 1 and all(c[2] == 0 for c in chunks[:-1])

    def attempt(blob: bytes, match: str) -> None:
        bad = tmp_path / "bad.enc"
        bad.write_bytes(blob)
        dest = tmp_path / "bad.out"
        with pytest.raises(EncryptionError, match=match):
            decrypt_file(bad, dest, PW)
        assert not dest.exists()
        bad.unlink()

    attempt(data[: chunks[-1][0]], "missing final chunk")  # last chunk dropped
    attempt(data[:-7], "truncated encrypted backup \\(chunk\\)")  # cut inside the last chunk
    a, b = chunks[0], chunks[1]
    swapped = data[: a[0]] + data[b[0] : b[1]] + data[a[0] : a[1]] + data[b[1] :]
    attempt(swapped, "wrong password, or")  # reordered chunks fail authentication
    attempt(data + b"\x00", "trailing data")
    attempt(data[: a[0]] + data[a[0] : a[1]] + data[a[0] :], "corrupted or tampered")  # duplicated

    def flip(blob: bytes, offset: int) -> bytes:
        b = bytearray(blob)
        b[offset] ^= 0x01
        return bytes(b)

    # the final flag is bound by the AAD: flipping it on a middle or the last chunk fails
    attempt(flip(data, chunks[0][0] + 4), "wrong password, or")  # chunk 0: indistinguishable
    attempt(flip(data, chunks[-1][0] + 4), "chunk 3; the password was accepted")
    # truncating after chunk 0 and marking it final does not make a complete file
    marked = bytearray(data[: chunks[1][0]])
    marked[chunks[0][0] + 4] = 1
    attempt(bytes(marked), "wrong password, or")
    # a tampered ciphertext length is caught by the bounds or by the tag
    attempt(flip(data, chunks[1][0]), "malformed chunk|truncated|corrupted or tampered")
    # damage after the first chunk names the chunk and says the password was fine
    attempt(flip(data, chunks[2][0] + 5 + 3), "chunk 2; the password was accepted")
    # the unmodified file still decrypts to the exact plaintext
    dest = tmp_path / "ok.out"
    decrypt_file(enc, dest, PW)
    assert dest.read_bytes() == plain.read_bytes()


def test_header_bounds_are_enforced_before_deriving(tmp_path: Path) -> None:
    plain = tmp_path / "p.bin"
    plain.write_bytes(b"x" * 100)
    enc = tmp_path / "p.enc"
    header = encrypt_file(plain, enc, PW, kdf_n=KDF_N)
    data = enc.read_bytes()
    header_len = struct.unpack(">I", data[len(backup_crypto.MAGIC) :][:4])[0]
    raw = data[len(backup_crypto.MAGIC) + 4 :][:header_len]

    def with_header(h: dict[str, object]) -> bytes:
        new = json.dumps(h, separators=(",", ":")).encode()
        return (
            backup_crypto.MAGIC
            + struct.pack(">I", len(new))
            + new
            + data[len(backup_crypto.MAGIC) + 4 + header_len :]
        )

    crafted = json.loads(raw)
    crafted["kdf"]["n"] = 1 << 30  # would need gigabytes of memory
    bad = tmp_path / "bad.enc"
    bad.write_bytes(with_header(crafted))
    with pytest.raises(EncryptionError, match="out of bounds"):
        decrypt_file(bad, tmp_path / "o1", PW)
    crafted = json.loads(raw)
    crafted["version"] = 2
    bad.write_bytes(with_header(crafted))
    with pytest.raises(EncryptionError, match="version 2"):
        decrypt_file(bad, tmp_path / "o2", PW)
    crafted = json.loads(raw)
    crafted["kdf"]["salt"] = base64.b64encode(b"short").decode()
    bad.write_bytes(with_header(crafted))
    with pytest.raises(EncryptionError, match="salt"):
        decrypt_file(bad, tmp_path / "o3", PW)
    # an honest header with a legitimately edited field still fails: the AAD binds the header
    crafted = json.loads(raw)
    crafted["inner"] = "tar"
    bad.write_bytes(with_header(crafted))
    with pytest.raises(EncryptionError, match="wrong password, or"):
        decrypt_file(bad, tmp_path / "o4", PW)
    assert header["chunk_size"] == backup_crypto.DEFAULT_CHUNK


def test_empty_password_and_plain_zip_paths(tmp_path: Path, source: str) -> None:
    with pytest.raises(BackupError, match="must not be empty"):
        create_backup(source, tmp_path / "x.enc", password="", kdf_n=KDF_N)
    with pytest.raises(BackupError, match="not valid Unicode"):
        create_backup(source, tmp_path / "y.enc", password="abc\udcff", kdf_n=KDF_N)
    assert not (tmp_path / "y.enc").exists()
    assert not (tmp_path / "x.enc").exists()
    plain_zip = tmp_path / "plain.zip"
    create_backup(source, plain_zip)
    assert not is_encrypted(plain_zip)
    m = inspect_backup(plain_zip, "ignored for a plain archive")
    assert m["_encrypted"] is False and m["encryption"] == "none"
    with pytest.raises(EncryptionError, match="not an encrypted"):
        decrypt_file(plain_zip, tmp_path / "never", PW)
    assert not (tmp_path / "never").exists()


def test_cli_round_trip_in_a_fresh_process(tmp_path: Path, source: str) -> None:
    """The CLI runs without the app imported elsewhere: the restore's schema allow-list must come
    from the ORM metadata even then (it was empty in a fresh process before 2026-09-21)."""
    script = Path(__file__).resolve().parents[2] / "scripts" / "backup.py"
    pw = tmp_path / "pw"
    pw.write_text("a-password-for-the-test\n")
    env = {**os.environ, "DATABASE_URL": source.replace("sqlite://", "sqlite+aiosqlite://")}
    out = tmp_path / "cli.zip.enc"

    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(script), *args],
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=script.parents[1] / "backend",
        )

    r = run("create", "--out", str(out), "--scope", "full", "--encrypt", "--password-file", str(pw))
    assert r.returncode == 0, r.stderr
    assert "encrypted (keep the password" in r.stdout
    r = run("inspect", str(out), "--password-file", str(pw))
    assert r.returncode == 0 and "encrypted envelope" in r.stdout, r.stderr
    wrong = tmp_path / "wrong"
    wrong.write_text("nope\n")
    r = run("restore", str(out), "--target", str(tmp_path / "t1"), "--password-file", str(wrong))
    assert r.returncode == 2 and "wrong password" in r.stderr and not (tmp_path / "t1").exists()
    r = run("restore", str(out), "--target", str(tmp_path / "t2"), "--password-file", str(pw))
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "t2" / "data" / "dev.db").is_file()
    assert dump_tables(f"sqlite:///{tmp_path / 't2' / 'data' / 'dev.db'}") == dump_tables(source)
