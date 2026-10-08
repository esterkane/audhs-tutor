"""Non-restored inference boundary proof; does not classify or resume database requests.

The caller must seal BEFORE gateway entry and stop if sealing fails. A DB snapshot can
rewind a phase but must never rewind this file. Unsupported/tampered evidence is unknown.
"""

import os
import re
import secrets
from pathlib import Path
from typing import Any

from app.core.local_ownership import LocalOwnership, OwnershipUnavailable


class AssessmentGuard:
    def __init__(self, owner: LocalOwnership, token: str) -> None:
        self.owner = owner
        self.token = token

    @property
    def receipt(self) -> dict[str, Any]:
        return {
            "version": 1,
            "device": self.owner.identity[0],
            "inode": self.owner.identity[1],
            "token": self.token,
        }

    @property
    def _prepared(self) -> bytes:
        return b"assessment-v1:" + self.token.encode("ascii") + b"\n"

    @classmethod
    def create(cls, database: Path, claim_id: str) -> "AssessmentGuard":
        owner = LocalOwnership.acquire(database, claim_id, namespace="assessment", create=True)
        if owner is None:
            raise OwnershipUnavailable("Assessment ownership is busy")
        guard = cls(owner, secrets.token_hex(16))
        try:
            if os.write(owner.descriptor, guard._prepared) != len(guard._prepared):
                raise OwnershipUnavailable("Incomplete assessment ownership marker")
            os.fsync(owner.descriptor)
            return guard
        except BaseException:
            owner.close()
            raise

    @classmethod
    def acquire_prepared(
        cls, database: Path, claim_id: str, receipt: dict[str, Any]
    ) -> "AssessmentGuard | None":
        return cls._acquire(database, claim_id, receipt, sealed=False)

    @classmethod
    def acquire_sealed(
        cls, database: Path, claim_id: str, receipt: dict[str, Any]
    ) -> "AssessmentGuard | None":
        """Observe released local ownership, never permission to repeat inference.

        A provider may still be running after its local caller exits. Keep this guard
        held while rechecking durable result state, then close it without mutation.
        """
        return cls._acquire(database, claim_id, receipt, sealed=True)

    @classmethod
    def _acquire(
        cls, database: Path, claim_id: str, receipt: dict[str, Any], *, sealed: bool
    ) -> "AssessmentGuard | None":
        if (
            type(receipt.get("version")) is not int
            or receipt["version"] != 1
            or any(
                type(receipt.get(key)) is not int or receipt[key] < 0 for key in ("device", "inode")
            )
            or not isinstance(receipt.get("token"), str)
            or re.fullmatch(r"[0-9a-f]{32}", receipt["token"]) is None
        ):
            raise OwnershipUnavailable("Invalid assessment ownership receipt")
        owner = LocalOwnership.acquire(
            database,
            claim_id,
            namespace="assessment",
            expected=(receipt["device"], receipt["inode"]),
        )
        if owner is None:
            return None
        guard = cls(owner, receipt["token"])
        try:
            expected = guard._prepared + (b"!" if sealed else b"")
            if os.pread(owner.descriptor, len(guard._prepared) + 2, 0) != expected:
                raise OwnershipUnavailable(
                    "Assessment may have entered inference; recovery is unknown"
                )
            return guard
        except BaseException:
            owner.close()
            raise

    def seal_inference(self) -> None:
        """Irreversibly mark this operation before gateway entry; failure forbids entry."""
        fd = self.owner.descriptor
        current = os.pread(fd, len(self._prepared) + 2, 0)
        if current == self._prepared + b"!":
            os.fsync(fd)
            return
        if current != self._prepared:
            raise OwnershipUnavailable("Assessment boundary marker is invalid")
        os.lseek(fd, 0, os.SEEK_END)
        if os.write(fd, b"!") != 1:
            raise OwnershipUnavailable("Assessment boundary marker was not written")
        os.fsync(fd)

    def close(self) -> None:
        self.owner.close()
