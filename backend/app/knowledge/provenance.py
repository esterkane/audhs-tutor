"""Provenance is first-class; retrieved text is untrusted data (ADR-0008)."""

import re
import unicodedata
from enum import IntEnum

from pydantic import BaseModel


class TrustTier(IntEnum):
    UNTRUSTED = 0  # arbitrary web text, forum posts
    WEB = 1  # reputable docs, blogs
    COURSE = 2  # purchased course material
    OWNER_VERIFIED = 3  # the learner checked it


class Provenance(BaseModel):
    source_id: str
    path: str
    source_type: str  # udemy_caption | slides | notebook | pdf | markdown | manual | synthetic
    trust_tier: int = TrustTier.COURSE
    course: str | None = None
    section: str | None = None
    lecture: str | None = None
    t_start: float | None = None
    t_end: float | None = None

    def citation(self) -> str:
        """`[course › section › lecture @mm:ss]` per prompts-and-pedagogy rule 5."""
        parts = [p for p in (self.course, self.section, self.lecture) if p]
        label = " › ".join(parts) if parts else self.path
        if self.t_start is not None:
            m, s = divmod(int(self.t_start), 60)
            label += f" @{m:02d}:{s:02d}"
        return f"[{label}]"


# Instruction-like content inside retrieved text is flagged, never obeyed.
_RAW_PATTERNS: dict[str, str] = {
    "ignore_previous": (
        r"\b(ignore|disregard|forget)\b.{0,40}\b(previous|prior|above|earlier)\b"
        r".{0,20}\b(instructions?|prompts?|rules?)\b"
    ),
    "role_override": (
        r"\byou are now (a|an|the|my|our)\b|\bact as\b.{0,30}\b(system|admin|developer)\b"
        r"|\bnew persona\b|\bfrom now on you\b"
    ),
    "system_prompt_ref": r"\bsystem prompt\b|\bdeveloper message\b",
    "exfiltration": (
        r"\b(reveal|print|output|leak|exfiltrate)\b.{0,30}"
        r"\b(system prompt|api keys?|secrets?|passwords?|(access|auth|api|bearer|session) tokens?|credentials?)\b"
    ),
    "hidden_directive": r"\bdo not (tell|inform|show)\b.{0,20}\b(the )?(user|learner)\b",
    "fake_markup": (
        r"</?\s*(system|assistant|instruction|tool_result|policy)\s*>|\[/?INST\]"
        r"|BEGIN (SYSTEM|INSTRUCTIONS)"
    ),
    "fake_section": r"(?m)^\s*#{1,3}\s+(output contract|request|session state|system|instructions?)\b",
    "tool_call_injection": (
        r"\bcall (the )?tool\b|\bexecute (this )?(command|code)\b|\brun (the )?following\b"
    ),
    "authority_claim": (
        r"\b(note|message|instruction)s? (for|to) (the )?(ai|assistant|model|llm|tutor)s?\b"
        r"|\bas (the|your) (developer|administrator|operator)\b"
    ),
    "encoded_blob": r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{120,}={0,2}(?![A-Za-z0-9+/])",
}
INSTRUCTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (name, re.compile(rx, re.IGNORECASE)) for name, rx in _RAW_PATTERNS.items()
]


_INVISIBLE = re.compile("[​‌‍⁠﻿­᠎‎‏‪-‮⁦-⁩]")


def scan_text(text: str) -> str:
    """What the patterns run on: NFKC (full-width / stylised letters → ASCII) with zero-width and
    bidi control characters removed, so `ig​nore` and `ｉｇｎｏｒｅ` still match."""
    return unicodedata.normalize("NFKC", _INVISIBLE.sub("", text))


def flag_instruction_patterns(text: str) -> list[str]:
    scanned = scan_text(text)
    flags = [name for name, rx in INSTRUCTION_PATTERNS if rx.search(scanned)]
    if flags and scanned != unicodedata.normalize("NFKC", text):
        flags.append("obfuscated")  # the pattern only showed after stripping invisible characters
    elif not flags and _INVISIBLE.search(text) and len(_INVISIBLE.findall(text)) >= 3:
        flags.append("obfuscated")  # invisible characters sprinkled through clean-looking text
    return flags
