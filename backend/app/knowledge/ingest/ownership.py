"""Same-host POSIX ownership proof for a future durable import recovery path.

An existing lock must be acquired before an abandoned run can be reconciled. Missing or
unsafe lock storage is UNKNOWN, never evidence of a dead worker. Do not unlink lock files:
replacing an inode would let two workers lock different files for the same run. This module
alone does not change run states or enable recovery. Network filesystems are not supported.
"""

from __future__ import annotations

import os
import re
import stat
from pathlib import Path
from types import TracebackType

try:
    import fcntl
except ImportError:  # unsupported platforms retain unknown ownership
    fcntl = None  # type: ignore[assignment]


class OwnershipUnavailable(RuntimeError):
    """Cannot establish ownership; the caller must not infer that a worker stopped."""


class RunOwnership:
    """Exclusive, nonblocking per-run lock. Use as a context manager; never delete its file."""

    def __init__(self, fd: int, identity: tuple[int, int]) -> None:
        self._fd: int | None = fd
        self.identity = identity

    @classmethod
    def acquire(
        cls,
        database: Path,
        run_id: str,
        *,
        create: bool = False,
        expected: tuple[int, int] | None = None,
    ) -> RunOwnership | None:
        """Return a held lock, None if busy, or raise when proof is unavailable.

        create=True is only for a NEW identity, before its running record is committed.
        Recovery uses create=False plus the identity persisted with the run: it must not
        manufacture missing evidence or trust a replacement inode. All callers
        must use the same canonical local SQLite path (hard-link aliases are unsupported).
        The caller runs this short nonblocking filesystem operation outside transactions.
        """
        if fcntl is None or not hasattr(os, "O_NOFOLLOW"):
            raise OwnershipUnavailable("Local import ownership requires POSIX file locks")
        if re.fullmatch(r"[0-9A-HJKMNP-TV-Z]{26}", run_id) is None:
            raise OwnershipUnavailable("Invalid import run identity")
        if (create and expected is not None) or (not create and expected is None):
            raise OwnershipUnavailable("Recovery requires the original lock identity")
        directory_fd: int | None = None
        file_fd: int | None = None
        try:
            canonical = database.resolve(strict=True)
            if not canonical.is_file():
                raise OwnershipUnavailable("Ownership requires an existing file-backed database")
            directory = canonical.with_name(canonical.name + ".ingest-locks")
            if create:
                try:
                    directory.mkdir(mode=0o700)
                except FileExistsError:
                    pass
            directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            metadata = os.fstat(directory_fd)
            if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o077:
                raise OwnershipUnavailable("Import lock directory must be private to this user")
            flags = os.O_RDWR | os.O_NOFOLLOW
            if create:
                flags |= os.O_CREAT | os.O_EXCL
            file_fd = os.open(run_id, flags, mode=0o600, dir_fd=directory_fd)
            metadata = os.fstat(file_fd)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) & 0o077
                or metadata.st_nlink != 1
            ):
                raise OwnershipUnavailable("Import lock must be a private regular file")
            identity = (metadata.st_dev, metadata.st_ino)
            if not create and identity != expected:
                raise OwnershipUnavailable("Import lock was replaced")
            try:
                fcntl.flock(file_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return None
            # Refuse a removed/replaced file even if its old inode was successfully locked.
            current = os.stat(run_id, dir_fd=directory_fd, follow_symlinks=False)
            if (current.st_dev, current.st_ino) != (metadata.st_dev, metadata.st_ino):
                raise OwnershipUnavailable("Import lock identity changed")
            owned = cls(file_fd, identity)
            file_fd = None  # ownership passes to the context manager
            return owned
        except OSError as error:
            raise OwnershipUnavailable("Import ownership could not be verified") from error
        finally:
            if file_fd is not None:
                os.close(file_fd)
            if directory_fd is not None:
                os.close(directory_fd)

    def close(self) -> None:
        if self._fd is not None:
            os.close(self._fd)  # also releases flock, including exceptional exits
            self._fd = None

    def __enter__(self) -> RunOwnership:
        if self._fd is None:
            raise OwnershipUnavailable("Import ownership has already been released")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
