"""Process-bound opaque content tokens; restarting requires refresh, not regrading."""

import hashlib
import hmac
import json
import secrets
from typing import Any

_KEY = secrets.token_bytes(32)


def token(content: dict[str, Any]) -> str:
    payload = json.dumps(
        content, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )
    return "ac1." + hmac.new(_KEY, payload.encode(), hashlib.sha256).hexdigest()


def recovery_fingerprint(content: dict[str, Any]) -> str:
    """Private durable identity, never sent to clients as a content token.

    Public tokens intentionally expire on process restart. Recovery needs stable
    equality without copying the hidden answer/rubric into another private record.
    """
    payload = json.dumps(
        content, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )
    return "assessment-recovery-v1:" + hashlib.sha256(payload.encode()).hexdigest()
