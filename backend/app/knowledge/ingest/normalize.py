"""Text normalisation for dedupe and for the instruction-pattern scan (ADR-0008).

`normalize()` is what the dedupe key is computed from: NFKC, zero-width and control characters
stripped, whitespace and case collapsed. It is never what we store or show — the stored chunk text
keeps its original form (minus zero-width characters, which have no legitimate use in course text
and are a known obfuscation trick)."""

import hashlib
import re
import unicodedata

# zero-width / invisible formatting characters used to hide text from regexes and reviewers
_ZERO_WIDTH = re.compile("[​‌‍⁠﻿­᠎‎‏‪-‮⁦-⁩]")
_WS = re.compile(r"\s+")
_CAPTION_NOISE = re.compile(r"\[(music|applause|laughter|inaudible|silence)\]|♪", re.IGNORECASE)


def strip_invisible(text: str) -> str:
    return _ZERO_WIDTH.sub("", text)


def normalize(text: str) -> str:
    """Canonical form for hashing and pattern scans: NFKC, invisibles removed, whitespace + case folded."""
    text = unicodedata.normalize("NFKC", strip_invisible(text))
    return _WS.sub(" ", text).strip().casefold()


def norm_hash(text: str) -> str:
    return hashlib.sha256(normalize(text).encode()).hexdigest()


def clean_caption_line(line: str) -> str:
    line = re.sub(r"<[^>]+>", "", line)  # <c.colorE5E5E5>, <00:00:01.000>, <i>
    line = _CAPTION_NOISE.sub("", line)
    line = re.sub(r"^\s*(>>|-)\s*", "", line)  # speaker change markers
    return _WS.sub(" ", line).strip()


def approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


# Course repos and student notebooks sometimes carry live credentials. They are never learning
# material, so obvious key literals are replaced before a chunk is stored or embedded.
# Only *literal* values are redacted: a quoted string of ≥ 12 chars, or a bare token of ≥ 16
# word/dash chars that is not followed by `.`, `(` or `[` (so `token = tokenizer.decode(ids)`,
# `secret = settings.SECRET_KEY` and `next_token = model.generate(...)` stay intact).
_SECRET_ASSIGN = re.compile(
    r"(?i)\b((?:api[_-]?key|secret(?:[_-]?key)?|access[_-]?token|auth[_-]?token|token|password"
    r"|passwd|authorization)\s*[:=]\s*)"
    r"(?:(['\"])([^'\"\s]{12,})\2|([A-Za-z0-9_\-]{16,})(?![\w.(\[]))"
)
_SECRET_LITERAL = re.compile(
    r"\b(sk-[A-Za-z0-9_\-]{16,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|hf_[A-Za-z0-9]{20,}"
    r"|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9\-]{10,}|AIza[0-9A-Za-z_\-]{30,}"
    r"|eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,})"
)


def redact_secrets(text: str) -> str:
    def _assign(m: re.Match[str]) -> str:
        quote = m.group(2) or ""
        return f"{m.group(1)}{quote}<redacted>{quote}"

    text = _SECRET_ASSIGN.sub(_assign, text)
    return _SECRET_LITERAL.sub("<redacted>", text)
