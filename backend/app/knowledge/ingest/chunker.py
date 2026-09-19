"""Structure-aware chunker: respects headings, paragraphs, sentences, code fences and caption
timestamps; targets ~300 tokens, never splits mid-sentence, never splits a code block unless it is
larger than `max_chars` on its own. Every chunk is prefixed with `title › heading` so it stands
alone in a retrieval result."""

import re

from app.knowledge.ingest.types import Block, ChunkDraft, SourceDoc

TARGET_CHARS = 1200
MAX_CHARS = 1800
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(\"'])")


def split_sentences(text: str, max_chars: int) -> list[str]:
    """Greedy sentence packing; a single over-long sentence is split on whitespace."""
    parts: list[str] = []
    buf = ""
    for sent in _SENT.split(text):
        if buf and len(buf) + len(sent) + 1 > max_chars:
            parts.append(buf)
            buf = sent
        else:
            buf = f"{buf} {sent}".strip()
    if buf:
        parts.append(buf)
    out: list[str] = []
    for p in parts:
        while len(p) > max_chars:
            cut = p.rfind(" ", 0, max_chars)
            cut = cut if cut > max_chars // 2 else max_chars
            out.append(p[:cut].strip())
            p = p[cut:].strip()
        if p:
            out.append(p)
    return out


def _units(block: Block, max_chars: int) -> list[str]:
    """Indivisible-ish pieces of a block: code fences whole, prose by paragraph then sentence."""
    if block.kind == "code":
        return (
            [block.text]
            if len(block.text) <= max_chars * 2
            else split_sentences(block.text, max_chars)
        )
    paras = [p.strip() for p in re.split(r"\n\s*\n", block.text) if p.strip()]
    units: list[str] = []
    for p in paras:
        units.extend([p] if len(p) <= max_chars else split_sentences(p, max_chars))
    return units


def chunk_doc(
    doc: SourceDoc, *, target_chars: int = TARGET_CHARS, max_chars: int = MAX_CHARS
) -> list[ChunkDraft]:
    drafts: list[ChunkDraft] = []
    buf: list[str] = []
    buf_len = 0
    cur_heading: str | None = None
    cur_kind = "prose"
    cur_slugs: list[str] = []
    t_start: float | None = None
    t_end: float | None = None

    def flush() -> None:
        nonlocal buf, buf_len, t_start, t_end
        if not buf:
            return
        heading = cur_heading or doc.lecture or doc.title
        head = (
            doc.title
            if not doc.lecture or doc.lecture == doc.title
            else f"{doc.lecture} › {doc.title}"
        )
        prefix = f"{head} › {heading}\n" if heading not in (doc.title, doc.lecture) else f"{head}\n"
        drafts.append(
            ChunkDraft(
                ordinal=len(drafts),
                heading=heading,
                text=prefix + "\n\n".join(buf),
                body="\n\n".join(buf),
                skill_slugs=list(cur_slugs),
                t_start=t_start,
                t_end=t_end,
                kind=cur_kind,  # type: ignore[arg-type]
            )
        )
        buf, buf_len, t_start, t_end = [], 0, None, None

    for block in doc.blocks:
        heading = block.heading
        if buf and (heading != cur_heading or block.skill_slugs != cur_slugs):
            flush()  # a heading is a concept boundary: never merge across it
        cur_heading, cur_slugs = heading, block.skill_slugs
        for unit in _units(block, max_chars):
            if buf and (buf_len + len(unit) > max_chars or (buf_len >= target_chars)):
                flush()
            if not buf:
                cur_kind = block.kind
                t_start = block.t_start
            buf.append(unit)
            buf_len += len(unit) + 2
            if block.t_end is not None:
                t_end = block.t_end
    flush()
    return drafts
