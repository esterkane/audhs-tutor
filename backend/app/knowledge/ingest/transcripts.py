"""Transcript formats beyond WebVTT/SRT -> cues -> the caption merger.

SubViewer (.sbv), Advanced SubStation (.ass/.ssa), TTML/DFXP (.ttml/.dfxp/.xml), JSON exports
(Whisper `segments`, YouTube json3 `events`, generic `[{start, end|duration, text}]`, podcast
`startTime/endTime/body`), Whisper TSV/CSV and timestamped plain text (`[00:12] …`, `00:12 …`,
Otter/Zoom "Speaker  0:12" lines). Every path ends in `Cue`s so `t_start`/`t_end` and `@mm:ss`
citations behave exactly like Udemy captions."""

import csv
import io
import json
import re
from typing import Any

from app.knowledge.ingest.captions import Cue, dedupe_rolling, merge_cues, parse_timestamp
from app.knowledge.ingest.normalize import clean_caption_line
from app.knowledge.ingest.types import Block
from app.knowledge.ingest.xmlsafe import parse_xml

TRANSCRIPT_SUFFIXES = {".sbv", ".ass", ".ssa", ".ttml", ".dfxp"}

_CLOCK = re.compile(r"^(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?:[.,:](\d{1,3}))?$")
_OFFSET = re.compile(r"^(\d+(?:\.\d+)?)(h|m|s|ms|t|f)?$")


def flex_seconds(raw: str, *, frame_rate: float = 30.0, tick_rate: float = 1.0) -> float:
    """`hh:mm:ss.fff`, `mm:ss`, `h:mm:ss.cc` (ASS), `hh:mm:ss:ff` (frames), `12.5s`, `1500ms`,
    `2m`, `1h`, `90000t` (ticks) or a bare number of seconds."""
    raw = raw.strip()
    m = _CLOCK.match(raw)
    if m:
        h, mi, s, frac = m.groups()
        secs = int(h or 0) * 3600 + int(mi) * 60 + int(s)
        if frac is None:
            return float(secs)
        if ":" in raw[raw.rfind(":") - 3 :] and raw.count(":") == 3:  # hh:mm:ss:ff
            return secs + int(frac) / frame_rate
        return float(secs + int(frac) / (10 ** len(frac)))
    m = _OFFSET.match(raw)
    if not m:
        raise ValueError(f"bad time: {raw!r}")
    value, unit = float(m.group(1)), m.group(2)
    return {
        None: value,
        "s": value,
        "ms": value / 1000,
        "m": value * 60,
        "h": value * 3600,
        "t": value / tick_rate,
        "f": value / frame_rate,
    }[unit]


# ----------------------------------------------------------------------------- SBV / ASS / TTML
_SBV_HEAD = re.compile(r"^\s*(\d{1,2}:\d{2}:\d{2}[.,]\d{3}),(\d{1,2}:\d{2}:\d{2}[.,]\d{3})\s*$")


def sbv_cues(raw: str) -> list[Cue]:
    cues: list[Cue] = []
    for block in re.split(r"\n\s*\n", raw.replace("\r\n", "\n")):
        lines = [ln for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue
        m = _SBV_HEAD.match(lines[0])
        if not m:
            continue
        text = " ".join(clean_caption_line(ln) for ln in lines[1:]).strip()
        if text:
            cues.append(Cue(parse_timestamp(m.group(1)), parse_timestamp(m.group(2)), text))
    return cues


_ASS_TAGS = re.compile(r"\{[^}]*\}")


def ass_cues(raw: str) -> list[Cue]:
    """`[Events]` section: the `Format:` line names the columns; `Dialogue:` rows carry the text as
    the last column (it may contain commas). Override tags `{\\an8}` are dropped, `\\N` is a break."""
    cols: list[str] = [
        "Layer",
        "Start",
        "End",
        "Style",
        "Name",
        "MarginL",
        "MarginR",
        "MarginV",
        "Effect",
        "Text",
    ]
    cues: list[Cue] = []
    for line in raw.replace("\r\n", "\n").split("\n"):
        if line.lower().startswith("format:"):
            cols = [c.strip() for c in line.split(":", 1)[1].split(",")]
        elif line.lower().startswith("dialogue:"):
            parts = line.split(":", 1)[1].split(",", len(cols) - 1)
            if len(parts) < len(cols):
                continue
            row = dict(zip(cols, (p.strip() for p in parts), strict=False))
            try:
                start, end = flex_seconds(row["Start"]), flex_seconds(row["End"])
            except (KeyError, ValueError):
                continue
            text = _ASS_TAGS.sub("", row.get("Text", "")).replace("\\N", " ").replace("\\n", " ")
            text = clean_caption_line(text).strip()
            if text:
                cues.append(Cue(start, end, text))
    cues.sort(key=lambda c: c.start)
    return cues


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def is_ttml(raw: str) -> bool:
    head = raw.lstrip()[:400].lower()
    return "<tt" in head and ("ttml" in head or "ttaf" in head or "<tt " in head or "<tt>" in head)


def ttml_cues(raw: str) -> list[Cue]:
    root = parse_xml(raw)
    frame_rate = float(next((v for k, v in root.attrib.items() if _local(k) == "frameRate"), 30))
    tick_rate = float(next((v for k, v in root.attrib.items() if _local(k) == "tickRate"), 1))
    cues: list[Cue] = []
    for p in root.iter():
        if _local(p.tag) != "p":
            continue
        begin = p.attrib.get("begin")
        if begin is None:
            continue
        try:
            start = flex_seconds(begin, frame_rate=frame_rate, tick_rate=tick_rate)
            if p.attrib.get("end"):
                end = flex_seconds(p.attrib["end"], frame_rate=frame_rate, tick_rate=tick_rate)
            elif p.attrib.get("dur"):
                end = start + flex_seconds(
                    p.attrib["dur"], frame_rate=frame_rate, tick_rate=tick_rate
                )
            else:
                end = start + 4.0
        except ValueError:
            continue
        parts: list[str] = []
        for node in p.iter():
            if node is not p and _local(node.tag) == "br":
                parts.append(" ")
            if node.text and _local(node.tag) != "metadata":
                parts.append(node.text)
            if node is not p and node.tail:
                parts.append(node.tail)
        text = clean_caption_line(" ".join(parts)).strip()
        if text:
            cues.append(Cue(start, end, text))
    cues.sort(key=lambda c: c.start)
    return cues


# ----------------------------------------------------------------------------- JSON / TSV / CSV
def _num(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        if isinstance(v, str):
            try:
                return flex_seconds(v)
            except ValueError:
                return None
        return None


def json_cues(obj: Any) -> list[Cue] | None:
    """Returns None when the JSON has no recognised transcript shape."""
    if isinstance(obj, dict):
        if isinstance(obj.get("segments"), list):
            return json_cues(obj["segments"])
        if isinstance(obj.get("events"), list):  # YouTube json3
            cues: list[Cue] = []
            for ev in obj["events"]:
                if not isinstance(ev, dict) or "segs" not in ev:
                    continue
                text = "".join(str(s.get("utf8", "")) for s in ev["segs"] if isinstance(s, dict))
                text = clean_caption_line(text.replace("\n", " ")).strip()
                if not text:
                    continue
                start = float(ev.get("tStartMs", 0)) / 1000
                end = start + float(ev.get("dDurationMs", 4000)) / 1000
                cues.append(Cue(start, end, text))
            return cues
        for key in ("transcript", "results", "items", "cues", "captions"):
            if isinstance(obj.get(key), list):
                inner = json_cues(obj[key])
                if inner:
                    return inner
        return None
    if not isinstance(obj, list) or not obj or not all(isinstance(x, dict) for x in obj):
        return None
    cues = []
    for seg in obj:
        text = seg.get("text") or seg.get("body") or seg.get("content") or seg.get("transcript")
        s0 = _num(seg.get("start", seg.get("startTime", seg.get("start_time", seg.get("offset")))))
        if not isinstance(text, str) or s0 is None:
            continue
        e0 = _num(seg.get("end", seg.get("endTime", seg.get("end_time"))))
        if e0 is None:
            dur = _num(seg.get("duration", seg.get("dur")))
            e0 = s0 + (dur if dur is not None else 4.0)
        text = clean_caption_line(text.replace("\n", " ")).strip()
        if text:
            cues.append(Cue(s0, e0, text))
    return cues or None


def tabular_cues(raw: str) -> list[Cue] | None:
    """Whisper `--output_format tsv` (start/end in ms) and CSVs with start/end(/duration)/text
    headers. Integer times above ten hours are read as milliseconds."""
    sample = raw[:2000]
    delim = "\t" if "\t" in sample.split("\n", 1)[0] else ","
    reader = csv.reader(io.StringIO(raw), delimiter=delim)
    try:
        header = [h.strip().lower() for h in next(reader)]
    except StopIteration:
        return None
    if "text" not in header or "start" not in header:
        return None
    i_start, i_text = header.index("start"), header.index("text")
    i_end = header.index("end") if "end" in header else None
    i_dur = header.index("duration") if "duration" in header else None
    rows: list[tuple[float, float | None, str]] = []
    for row in reader:
        if len(row) <= max(i_start, i_text):
            continue
        start = _num(row[i_start])
        if start is None:
            continue
        end = _num(row[i_end]) if i_end is not None and len(row) > i_end else None
        if end is None and i_dur is not None and len(row) > i_dur:
            dur = _num(row[i_dur])
            end = None if dur is None else -dur  # marker: relative
        rows.append((start, end, row[i_text]))
    if not rows:
        return None
    all_int = all(float(r[0]).is_integer() for r in rows)
    scale = 1000.0 if all_int and max(r[0] for r in rows) > 36_000 else 1.0
    cues: list[Cue] = []
    for start, end, text in rows:
        s = start / scale
        if end is None:
            e = s + 4.0
        elif end < 0:
            e = s + (-end) / scale
        else:
            e = end / scale
        text = clean_caption_line(text.replace("\n", " ")).strip()
        if text:
            cues.append(Cue(s, e, text))
    return cues or None


# ----------------------------------------------------------------------------- timestamped text
_TS_TOKEN = r"(?:\d{1,2}:)?\d{1,2}:\d{2}(?:[.,]\d{1,3})?"
_LEAD_TS = re.compile(
    rf"^\s*[\[(<]?\s*({_TS_TOKEN})\s*(?:-->?\s*({_TS_TOKEN}))?\s*[\])>]?\s*[-–—:]?\s*(.*\S)?\s*$"
)
_SPEAKER_TS = re.compile(rf"^\s*(.{{1,60}}?)\s+[\[(]?({_TS_TOKEN})[\])]?\s*:?\s*$")
_TRAIL_TS = re.compile(rf"^\s*(.*\S)\s+[\[(]({_TS_TOKEN})[\])]\s*$")


def timestamped_text_cues(raw: str, *, min_ratio: float = 0.4) -> list[Cue] | None:
    """Plain-text transcripts: a leading `[00:12]` / `00:12 -` per line, a trailing `(00:12)`, or
    Otter/Zoom style `Speaker  0:12` header lines followed by the utterance. Returns None when
    fewer than `min_ratio` of the non-empty lines carry a time (then the file is prose)."""
    lines = [ln.rstrip() for ln in raw.replace("\r\n", "\n").split("\n")]
    non_empty = [ln for ln in lines if ln.strip()]
    if len(non_empty) < 3:
        return None
    items: list[tuple[float, float | None, str]] = []
    pending: tuple[float, str] | None = None  # speaker-line time waiting for its text
    timed_lines = 0
    for ln in lines:
        if not ln.strip():
            continue
        m = _LEAD_TS.match(ln)
        if m and m.group(3):
            timed_lines += 1
            start = flex_seconds(m.group(1))
            end = flex_seconds(m.group(2)) if m.group(2) else None
            items.append((start, end, m.group(3)))
            pending = None
            continue
        m = _SPEAKER_TS.match(ln)
        if m:
            timed_lines += 1
            pending = (flex_seconds(m.group(2)), m.group(1).strip())
            continue
        m = _TRAIL_TS.match(ln)
        if m:
            timed_lines += 1
            items.append((flex_seconds(m.group(2)), None, m.group(1)))
            pending = None
            continue
        if pending is not None:
            start, speaker = pending
            items.append((start, None, f"{speaker}: {ln.strip()}"))
            pending = None
        elif items:
            s, e, t = items[-1]
            items[-1] = (s, e, f"{t} {ln.strip()}")
    if timed_lines / len(non_empty) < min_ratio or len(items) < 3:
        return None
    cues: list[Cue] = []
    for i, (start, end, text) in enumerate(items):
        if end is None:
            end = items[i + 1][0] if i + 1 < len(items) else start + 5.0
            end = max(end, start + 0.5)
        text = clean_caption_line(text).strip()
        if text:
            cues.append(Cue(start, end, text))
    return cues or None


# ----------------------------------------------------------------------------- dispatch
def transcript_cues(raw: str, suffix: str) -> list[Cue] | None:
    """Cues for a known transcript suffix, or a sniffed `.txt/.json/.xml/.tsv/.csv`; None when the
    content is not a transcript."""
    suffix = suffix.lower()
    if suffix == ".sbv":
        return sbv_cues(raw)
    if suffix in (".ass", ".ssa"):
        return ass_cues(raw)
    if suffix in (".ttml", ".dfxp") or (suffix == ".xml" and is_ttml(raw)):
        return ttml_cues(raw)
    if suffix == ".json":
        try:
            return json_cues(json.loads(raw))
        except json.JSONDecodeError:
            return None
    if suffix in (".tsv", ".csv"):
        return tabular_cues(raw)
    if suffix in (".txt", ".text", ".transcript"):
        return timestamped_text_cues(raw)
    return None


def transcript_blocks(cues: list[Cue]) -> list[Block]:
    return merge_cues(dedupe_rolling(cues))
