"""Password-based, authenticated encryption envelope for backup archives (ADR-0012).

Layout of an encrypted backup (`.zip.enc` by convention):

    MAGIC | u32 header length | header JSON | chunk | chunk | … | final chunk

`header` (plain JSON, integrity-bound through the AAD of every chunk — a tampered header makes every
chunk fail to authenticate) carries the format/version, the scrypt parameters and salt, the cipher
name, the plaintext chunk size and an 8-byte nonce prefix. It never carries the key or the password.
Each chunk is `u32 ciphertext length | u8 final flag | AES-256-GCM ciphertext` with
`nonce = prefix ‖ u32 chunk index` and `AAD = sha256(header) ‖ u32 chunk index ‖ u8 final flag`, so
a chunk cannot be reordered, dropped, duplicated or moved between files, and a missing final chunk
is detected as truncation. Memory stays bounded by the chunk size (1 MiB) on both sides — no
whole-file Fernet. Wrong password and corruption are indistinguishable by design (GCM tag failure)
and are reported as one refusal.
"""

import base64
import hashlib
import json
import os
import struct
import unicodedata
from pathlib import Path
from typing import Any, BinaryIO

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

MAGIC = b"AUDHS-TUTOR-BACKUP-ENC\n"
ENC_FORMAT = "audhs-tutor-backup-encrypted"
ENC_VERSION = 1
CIPHER = "aes-256-gcm"
KDF = "scrypt"
DEFAULT_KDF_N = 1 << 17  # ~128 MiB, ~0.3 s on an M-series Mac
KDF_R = 8
KDF_P = 1
MAX_KDF_N = 1 << 18  # bound the memory a crafted header can demand (≈ 256 MiB at r=8)
MIN_KDF_N = 1 << 10
DEFAULT_CHUNK = 1 << 20
MAX_CHUNK = 8 << 20
MAX_HEADER = 4096
MAX_CHUNKS = (1 << 32) - 1
TAG_LEN = 16
SALT_LEN = 16
PREFIX_LEN = 8
_CHUNK_HDR = struct.Struct(">IB")  # ciphertext length, final flag


class EncryptionError(ValueError):
    """Wrong password, tampering, truncation or an unsupported envelope."""


def _normalise_password(password: str) -> bytes:
    if not isinstance(password, str) or not password:
        raise EncryptionError("a non-empty password is required")
    try:
        return unicodedata.normalize("NFC", password).encode("utf-8")
    except UnicodeEncodeError as e:
        raise EncryptionError("the password is not valid Unicode text") from e


def _derive(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return Scrypt(salt=salt, length=32, n=n, r=r, p=p).derive(_normalise_password(password))


def _aad(header_hash: bytes, index: int, final: bool) -> bytes:
    return header_hash + struct.pack(">IB", index, 1 if final else 0)


def _nonce(prefix: bytes, index: int) -> bytes:
    return prefix + struct.pack(">I", index)


def is_encrypted(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            return f.read(len(MAGIC)) == MAGIC
    except OSError:
        return False


def read_header(path: Path) -> dict[str, Any]:
    """The plain header (never secret material) — refused when malformed or out of bounds."""
    with path.open("rb") as f:
        header = _read_header(f)
    header.pop("_raw", None)
    return header


def _read_header(f: BinaryIO) -> dict[str, Any]:
    if f.read(len(MAGIC)) != MAGIC:
        raise EncryptionError("not an encrypted tutor backup")
    raw_len = f.read(4)
    if len(raw_len) != 4:
        raise EncryptionError("truncated encrypted backup (no header)")
    (n,) = struct.unpack(">I", raw_len)
    if n == 0 or n > MAX_HEADER:
        raise EncryptionError("malformed encrypted backup (header length)")
    raw = f.read(n)
    if len(raw) != n:
        raise EncryptionError("truncated encrypted backup (header)")
    try:
        header = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise EncryptionError("malformed encrypted backup (header is not JSON)") from e
    if not isinstance(header, dict) or header.get("format") != ENC_FORMAT:
        raise EncryptionError("not an encrypted tutor backup (unknown format)")
    if header.get("version") != ENC_VERSION:
        raise EncryptionError(
            f"encrypted backup version {header.get('version')!r} is not supported "
            f"(this build reads version {ENC_VERSION})"
        )
    if header.get("cipher") != CIPHER:
        raise EncryptionError("unsupported cipher in encrypted backup")
    kdf = header.get("kdf")
    if not isinstance(kdf, dict) or kdf.get("name") != KDF:
        raise EncryptionError("unsupported key derivation in encrypted backup")
    n_, r_, p_ = kdf.get("n"), kdf.get("r"), kdf.get("p")
    if not (isinstance(n_, int) and isinstance(r_, int) and isinstance(p_, int)):
        raise EncryptionError("malformed key derivation parameters")
    if not (MIN_KDF_N <= n_ <= MAX_KDF_N and n_ & (n_ - 1) == 0 and 1 <= r_ <= 8 and 1 <= p_ <= 4):
        raise EncryptionError("key derivation parameters out of bounds (refusing to derive)")
    try:
        salt = base64.b64decode(kdf.get("salt", ""), validate=True)
        prefix = base64.b64decode(header.get("nonce_prefix", ""), validate=True)
    except (ValueError, TypeError) as e:
        raise EncryptionError("malformed salt or nonce prefix") from e
    if len(salt) != SALT_LEN or len(prefix) != PREFIX_LEN:
        raise EncryptionError("malformed salt or nonce prefix")
    chunk = header.get("chunk_size")
    if not isinstance(chunk, int) or not (1 <= chunk <= MAX_CHUNK):
        raise EncryptionError("chunk size out of bounds")
    header["_raw"] = raw
    return header


def encrypt_file(
    src: Path,
    dst: Path,
    password: str,
    *,
    kdf_n: int = DEFAULT_KDF_N,
    chunk_size: int = DEFAULT_CHUNK,
) -> dict[str, Any]:
    """Stream `src` into a new file `dst` (created exclusively). Returns the public header."""
    if not (MIN_KDF_N <= kdf_n <= MAX_KDF_N and kdf_n & (kdf_n - 1) == 0):
        raise EncryptionError("kdf_n must be a power of two within bounds")
    if not (1 <= chunk_size <= MAX_CHUNK):
        raise EncryptionError("chunk_size out of bounds")
    salt = os.urandom(SALT_LEN)
    prefix = os.urandom(PREFIX_LEN)
    header: dict[str, Any] = {
        "format": ENC_FORMAT,
        "version": ENC_VERSION,
        "cipher": CIPHER,
        "kdf": {
            "name": KDF,
            "n": kdf_n,
            "r": KDF_R,
            "p": KDF_P,
            "salt": base64.b64encode(salt).decode(),
        },
        "chunk_size": chunk_size,
        "nonce_prefix": base64.b64encode(prefix).decode(),
        "inner": "zip",
    }
    raw = json.dumps(header, separators=(",", ":")).encode()
    header_hash = hashlib.sha256(raw).digest()
    key = _derive(password, salt, kdf_n, KDF_R, KDF_P)
    aead = AESGCM(key)
    fd = os.open(dst, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "wb") as out, src.open("rb") as inp:
            out.write(MAGIC)
            out.write(struct.pack(">I", len(raw)))
            out.write(raw)
            index = 0
            block = inp.read(chunk_size)
            while True:
                nxt = inp.read(chunk_size)
                final = not nxt
                if index > MAX_CHUNKS:
                    raise EncryptionError("input too large for one envelope")
                ct = aead.encrypt(_nonce(prefix, index), block, _aad(header_hash, index, final))
                out.write(_CHUNK_HDR.pack(len(ct), 1 if final else 0))
                out.write(ct)
                if final:
                    break
                block, index = nxt, index + 1
    except BaseException:
        dst.unlink(missing_ok=True)
        raise
    return header


def decrypt_file(src: Path, dst: Path, password: str) -> dict[str, Any]:
    """Stream `src` into a new file `dst` (created exclusively); any failure removes `dst`.
    Refuses on wrong password, tampering, reordering, truncation or trailing data."""
    fd = os.open(dst, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "wb") as out, src.open("rb") as inp:
            header = _read_header(inp)
            raw = header.pop("_raw")
            header_hash = hashlib.sha256(raw).digest()
            kdf = header["kdf"]
            salt = base64.b64decode(kdf["salt"])
            prefix = base64.b64decode(header["nonce_prefix"])
            chunk_size = int(header["chunk_size"])
            aead = AESGCM(_derive(password, salt, kdf["n"], kdf["r"], kdf["p"]))
            index = 0
            while True:
                hdr = inp.read(_CHUNK_HDR.size)
                if len(hdr) != _CHUNK_HDR.size:
                    raise EncryptionError("truncated encrypted backup (missing final chunk)")
                ct_len, flag = _CHUNK_HDR.unpack(hdr)
                if flag not in (0, 1) or ct_len < TAG_LEN or ct_len > chunk_size + TAG_LEN:
                    raise EncryptionError("malformed chunk in encrypted backup")
                ct = inp.read(ct_len)
                if len(ct) != ct_len:
                    raise EncryptionError("truncated encrypted backup (chunk)")
                final = flag == 1
                try:
                    pt = aead.decrypt(_nonce(prefix, index), ct, _aad(header_hash, index, final))
                except InvalidTag as e:
                    # only the first chunk cannot tell a wrong password from damage; after it the
                    # password is proven, so say what actually happened
                    raise EncryptionError(
                        "wrong password, or the encrypted backup is corrupted or tampered with"
                        if index == 0
                        else "the encrypted backup is corrupted or tampered with "
                        f"(chunk {index}; the password was accepted)"
                    ) from e
                out.write(pt)
                if final:
                    if inp.read(1):
                        raise EncryptionError("trailing data after the final chunk")
                    break
                index += 1
                if index > MAX_CHUNKS:
                    raise EncryptionError("chunk count out of bounds")
        return header
    except BaseException:
        dst.unlink(missing_ok=True)
        raise
