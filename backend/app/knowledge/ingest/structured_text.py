"""Plain-text families with light structure: reStructuredText, Org, AsciiDoc, Textile and `.txt`
(paragraphs). Headings become block headings (concept boundaries for the chunker); everything else
is a paragraph. No markup rendering — the text is kept as written."""

import re

from app.knowledge.ingest.types import Block

_ORG = re.compile(r"^\*{1,4}\s+(.+?)\s*$")
_ADOC = re.compile(r"^={1,4}\s+(.+?)\s*$")
_MD = re.compile(r"^#{1,4}\s+(.+?)\s*$")
_RST_UNDERLINE = re.compile(r"^([=\-~^\"'`#*+_:.])\1{2,}\s*$")
_TEXTILE = re.compile(r"^h[1-4]\.\s+(.+?)\s*$")
_ADOC_ATTR = re.compile(r"^:[\w-]+:.*$")

STRUCTURED_SUFFIXES = {".rst", ".org", ".adoc", ".asciidoc", ".textile", ".txt", ".text"}


def structured_blocks(text: str) -> list[Block]:
    lines = text.replace("\r\n", "\n").split("\n")
    blocks: list[Block] = []
    heading: str | None = None
    para: list[str] = []

    def flush() -> None:
        nonlocal para
        body = "\n".join(para).strip()
        if body:
            blocks.append(Block(text=body, kind="prose", heading=heading))
        para = []

    i = 0
    while i < len(lines):
        ln = lines[i]
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if ln.strip() and _RST_UNDERLINE.match(nxt) and len(nxt.strip()) >= len(ln.strip()):
            flush()
            heading = ln.strip()
            i += 2
            if i < len(lines) and _RST_UNDERLINE.match(lines[i]):  # overline+underline titles
                i += 1
            continue
        m = _ORG.match(ln) or _ADOC.match(ln) or _MD.match(ln) or _TEXTILE.match(ln)
        if m and not (ln.startswith("**") and ln.rstrip().endswith("**")):  # `**bold**` line
            flush()
            heading = m.group(1)
        elif _ADOC_ATTR.match(ln):
            pass  # asciidoc document attributes
        elif not ln.strip():
            flush()
        else:
            para.append(ln)
        i += 1
    flush()
    return blocks
