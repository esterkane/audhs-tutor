"""Markdown source loader: YAML front matter + `## heading {skill: slug}` sections -> chunks.

Chunks are section-based (one concept per section), split on paragraph boundaries when a
section exceeds `max_chars`, and prefixed with `title › heading` so a chunk stands alone.
"""

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

import yaml

_FRONT = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
_HEADING = re.compile(r"^##\s+(.*?)\s*(?:\{(skills?):\s*([^}]*)\})?\s*$", re.M)


@dataclass
class Section:
    heading: str
    text: str
    skill_slugs: list[str] = field(default_factory=list)


@dataclass
class MarkdownDoc:
    meta: dict[str, Any]
    title: str
    body: str
    sections: list[Section]
    content_hash: str


@dataclass
class ChunkDraft:
    ordinal: int
    heading: str
    text: str
    skill_slugs: list[str]


def parse_markdown(raw: str) -> MarkdownDoc:
    meta: dict[str, Any] = {}
    body = raw
    m = _FRONT.match(raw)
    if m:
        meta = yaml.safe_load(m.group(1)) or {}
        body = raw[m.end() :]
    title = str(meta.get("title") or "Untitled")
    sections: list[Section] = []
    matches = list(_HEADING.finditer(body))
    for i, h in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        text = body[h.end() : end].strip()
        slugs = [s.strip() for s in (h.group(3) or "").split(",") if s.strip()]
        sections.append(Section(heading=h.group(1).strip(), text=text, skill_slugs=slugs))
    return MarkdownDoc(
        meta=meta,
        title=title,
        body=body,
        sections=sections,
        content_hash=hashlib.sha256(raw.encode()).hexdigest(),
    )


def chunk_sections(doc: MarkdownDoc, *, max_chars: int = 1800) -> list[ChunkDraft]:
    out: list[ChunkDraft] = []
    for sec in doc.sections:
        prefix = f"{doc.title} › {sec.heading}\n"
        paras = [p.strip() for p in re.split(r"\n\s*\n", sec.text) if p.strip()]
        buf: list[str] = []
        size = 0
        for p in paras:
            if buf and size + len(p) > max_chars:
                out.append(
                    ChunkDraft(len(out), sec.heading, prefix + "\n\n".join(buf), sec.skill_slugs)
                )
                buf, size = [], 0
            buf.append(p)
            size += len(p)
        if buf:
            out.append(
                ChunkDraft(len(out), sec.heading, prefix + "\n\n".join(buf), sec.skill_slugs)
            )
    return out


def approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)
