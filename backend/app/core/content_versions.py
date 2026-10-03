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
