"""HTML/XHTML -> blocks with the stdlib parser. Headings h1–h4 set the current heading, block
elements delimit paragraphs, `<pre>` becomes a code block, tables become `| a | b |` rows,
list items get a bullet. `script`, `style`, `nav`, `header`, `footer`, `aside`, `template`,
`svg` and hidden inputs are dropped. Attributes never reach the output (ADR-0008 does not care
about markup, only about text — but no `onload=` string should become learning material)."""

import re
from html import unescape
from html.parser import HTMLParser

from app.knowledge.ingest.types import Block

_SKIP = {
    "script",
    "style",
    "noscript",
    "nav",
    "header",
    "footer",
    "aside",
    "template",
    "svg",
    "iframe",
    "canvas",
    "button",
    "select",
    "form",
}
_BLOCK = {
    "p",
    "div",
    "section",
    "article",
    "main",
    "blockquote",
    "figure",
    "figcaption",
    "dd",
    "dt",
    "address",
    "details",
    "summary",
    "hr",
    "br",
    "ul",
    "ol",
    "table",
    "thead",
    "tbody",
    "tfoot",
    "body",
    "html",
    "h5",
    "h6",
}
_HEADINGS = {"h1", "h2", "h3", "h4"}
_VOID = {"br", "hr", "img", "input", "meta", "link"}


class _Extractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.blocks: list[Block] = []
        self.heading: str | None = None
        self._skip = 0
        self._in_title = False
        self._head: list[str] | None = None
        self._pre: list[str] | None = None
        self._para: list[str] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._table: list[str] | None = None
        self._li = False

    # -- helpers
    def _flush_para(self) -> None:
        text = re.sub(r"[ \t\r\n]+", " ", "".join(self._para)).strip()
        self._para = []
        if text:
            self.blocks.append(Block(text=text, kind="prose", heading=self.heading))

    def _emit_table(self) -> None:
        rows = [r for r in (self._table or []) if r.strip(" |")]
        self._table = None
        if rows:
            self.blocks.append(
                Block(text="\n".join(rows[:200]), kind="table", heading=self.heading)
            )

    # -- parser callbacks
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in _SKIP:
            self._skip += 1
            return
        if self._skip:
            return
        if tag == "title":
            self._in_title = True
        elif tag in _HEADINGS:
            self._flush_para()
            self._head = []
        elif tag == "pre":
            self._flush_para()
            self._pre = []
        elif tag == "table":
            self._flush_para()
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []
        elif tag == "li":
            self._flush_para()
            self._li = True
            self._para.append("• ")
        elif tag in _BLOCK:
            self._flush_para()
        elif tag == "img":
            alt = dict(attrs).get("alt")
            if alt and alt.strip():
                self._para.append(f" [image: {alt.strip()}] ")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _SKIP:
            self._skip = max(0, self._skip - 1)
            return
        if self._skip:
            return
        if tag == "title":
            self._in_title = False
        elif tag in _HEADINGS and self._head is not None:
            text = re.sub(r"\s+", " ", "".join(self._head)).strip()
            self._head = None
            if text:
                self.heading = text
        elif tag == "pre" and self._pre is not None:
            code = "".join(self._pre).strip("\n")
            self._pre = None
            if code.strip():
                self.blocks.append(
                    Block(text=f"```\n{code}\n```", kind="code", heading=self.heading)
                )
        elif tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._row.append(re.sub(r"\s+", " ", "".join(self._cell)).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            self._table.append("| " + " | ".join(self._row) + " |")
            self._row = None
        elif tag == "table" and self._table is not None:
            self._emit_table()
        elif tag == "li":
            self._li = False
            self._flush_para()
        elif tag in _BLOCK:
            self._flush_para()

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in _VOID:
            self.handle_starttag(tag, attrs)
            if tag.lower() in ("br", "hr"):
                self._flush_para()

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        if self._in_title:
            self.title += data
        elif self._head is not None:
            self._head.append(data)
        elif self._pre is not None:
            self._pre.append(data)
        elif self._cell is not None:
            self._cell.append(data)
        elif self._row is not None or self._table is not None:
            return  # whitespace between cells
        else:
            self._para.append(data)


def html_blocks(raw: str) -> tuple[str | None, list[Block]]:
    p = _Extractor()
    p.feed(raw)
    p.close()
    p._flush_para()
    if p._table is not None:
        p._emit_table()
    title = re.sub(r"\s+", " ", unescape(p.title)).strip() or None
    return title, p.blocks
