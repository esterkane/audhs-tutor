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
