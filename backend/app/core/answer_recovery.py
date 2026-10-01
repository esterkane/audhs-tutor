"""Process-bound signed save receipts; no model calls, disk writes or learning evidence."""

import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from app.core.errors import AppError

MAX_RECEIPT = 550_000
TTL_SECONDS = 3600


class AnswerRecovery:
    """The client carries the snapshot; the server retains only a process-local signing key.

    Restart intentionally invalidates receipts. Ownership and session existence are also
    checked on recovery; a receipt cannot restore a wiped session or forge model provenance.
    """

    def __init__(self) -> None:
        self._key = secrets.token_bytes(32)

    def issue(self, snapshot: dict[str, Any]) -> str | None:
        encoded = base64.urlsafe_b64encode(
            json.dumps(
                {"expires": int(time.time()) + TTL_SECONDS, "snapshot": snapshot},
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode()
        ).decode()
        signature = hmac.new(self._key, encoded.encode(), hashlib.sha256).hexdigest()
        receipt = encoded + "." + signature
        return receipt if len(receipt) <= MAX_RECEIPT else None

    def read(self, receipt: str, learner_id: str) -> dict[str, Any]:
        try:
            if len(receipt) > MAX_RECEIPT:
                raise ValueError
            encoded, signature = receipt.rsplit(".", 1)
            expected = hmac.new(self._key, encoded.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected):
                raise ValueError
            payload = json.loads(base64.b64decode(encoded, altchars=b"-_", validate=True))
            snapshot = payload["snapshot"]
            if payload["expires"] <= time.time() or snapshot["learner_id"] != learner_id:
                raise ValueError
            if not isinstance(snapshot, dict):
                raise ValueError
            return snapshot
        except (ValueError, KeyError, TypeError, binascii.Error) as exc:
            raise AppError(
                "save_receipt_unavailable",
                "This save receipt expired or the server restarted. Keep a copy of the visible answer.",
                http_status=410,
            ) from exc
