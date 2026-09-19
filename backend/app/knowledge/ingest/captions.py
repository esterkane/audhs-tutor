"""WebVTT / SRT captions (Udemy exports) -> timed caption blocks.

Udemy auto-captions are short rolling cues (2–6 s). We drop cue-level duplicates (the classic
"same line repeated in overlapping cues"), join cues into time-windowed paragraphs and keep
`t_start`/`t_end` on every block so a citation can point at `@mm:ss`."""

import re
from dataclasses import dataclass

from app.knowledge.ingest.normalize import clean_caption_line
from app.knowledge.ingest.types import Block

_TS = re.compile(
    r"(?P<h>\d{1,2}):(?P<m>\d{2}):(?P<s>\d{2})[.,](?P<ms>\d{3})|(?P<m2>\d{1,2}):(?P<s2>\d{2})[.,](?P<ms2>\d{3})"
)
_CUE_LINE = re.compile(r"^\s*(\S+)\s+-->\s+(\S+)")


@dataclass
class Cue:
    start: float
    end: float
    text: str


def parse_timestamp(raw: str) -> float:
    m = _TS.match(raw.strip())
    if not m:
        raise ValueError(f"bad timestamp: {raw!r}")
    if m.group("h") is not None:
        return (
            int(m.group("h")) * 3600
            + int(m.group("m")) * 60
            + int(m.group("s"))
            + int(m.group("ms")) / 1000
        )
    return int(m.group("m2")) * 60 + int(m.group("s2")) + int(m.group("ms2")) / 1000


def parse_cues(raw: str) -> list[Cue]:
    """Parses both WebVTT (with header/NOTE/STYLE blocks) and SRT (numbered cues)."""
    raw = raw.replace("\r\n", "\n").lstrip("﻿")
    cues: list[Cue] = []
    for block in re.split(r"\n\s*\n", raw):
        lines = [ln for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue
        idx = next((i for i, ln in enumerate(lines) if _CUE_LINE.match(ln)), None)
        if idx is None:
            continue  # WEBVTT header, NOTE, STYLE, or a stray SRT index
        m = _CUE_LINE.match(lines[idx])
        assert m is not None
        try:
            start, end = parse_timestamp(m.group(1)), parse_timestamp(m.group(2))
        except ValueError:
            continue
        text = " ".join(clean_caption_line(ln) for ln in lines[idx + 1 :]).strip()
        if text:
            cues.append(Cue(start, end, text))
    return cues


def dedupe_rolling(cues: list[Cue]) -> list[Cue]:
    """Auto-caption exports repeat the previous line in the next cue (rolling display). Remove
    exact repeats and the repeated prefix of the following cue."""
    out: list[Cue] = []
    for cue in cues:
        if out:
            prev = out[-1]
            if cue.text == prev.text:
                prev.end = max(prev.end, cue.end)
                continue
            if cue.text.startswith(prev.text + " "):
                cue = Cue(cue.start, cue.end, cue.text[len(prev.text) :].strip())
            elif prev.text.endswith(cue.text):
                prev.end = max(prev.end, cue.end)
                continue
        out.append(cue)
    return out


def merge_cues(
    cues: list[Cue], *, max_chars: int = 900, max_seconds: float = 90.0, gap_break: float = 4.0
) -> list[Block]:
    """Join cues into paragraphs: break on a long silence, on a sentence end once the window is
    large enough, and hard-break on max size/duration."""
    blocks: list[Block] = []
    buf: list[Cue] = []
    size = 0

    def flush() -> None:
        nonlocal buf, size
        if buf:
            blocks.append(
                Block(
                    text=" ".join(c.text for c in buf),
                    kind="caption",
                    t_start=buf[0].start,
                    t_end=buf[-1].end,
                )
            )
        buf, size = [], 0

    for cue in cues:
        if buf:
            span = cue.end - buf[0].start
            gap = cue.start - buf[-1].end
            ends_sentence = buf[-1].text.rstrip()[-1:] in ".?!"
            if (
                gap > gap_break
                or size + len(cue.text) > max_chars
                or span > max_seconds
                or (ends_sentence and size > max_chars * 0.6)
            ):
                flush()
        buf.append(cue)
        size += len(cue.text) + 1
    flush()
    return blocks


def caption_blocks(raw: str) -> list[Block]:
    return merge_cues(dedupe_rolling(parse_cues(raw)))
