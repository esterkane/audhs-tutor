"""Extract named CLI and self-hosting sections from Supabase's aggregate HTML."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

SECTION_URL = re.compile(
    r"https://supabase\.com/docs/reference/(cli|self-hosting-(?:analytics|auth|functions|realtime|storage))/([a-z0-9-]+)/?"
)
_VOID = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


@dataclass
class _Node:
    tag: str
    attrs: dict
    children: list[_Node | str] = field(default_factory=list)
    closed: bool = False


class _Sections(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack: list[_Node] = []
        self.ignore: list[str] = []
        self.ids: dict[str, list[_Node]] = {}

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if (
            self.ignore
            or tag in {"script", "style", "nav", "aside", "footer", "svg", "template"}
            or attributes.get("aria-hidden") == "true"
            or "hidden" in attributes
        ):
            if tag not in _VOID:
                self.ignore.append(tag)
            return
        if not self.stack and tag != "section":
            return
        node = _Node(tag, attributes)
        if self.stack:
            self.stack[-1].children.append(node)
        if tag == "section" and node.attrs.get("id"):
            self.ids.setdefault(node.attrs["id"], []).append(node)
        if tag not in _VOID:
            self.stack.append(node)

    def handle_endtag(self, tag):
        if self.ignore:
            if self.ignore[-1] == tag:
                self.ignore.pop()
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i].tag == tag:
                self.stack[i].closed = True
                del self.stack[i:]
                break

    def handle_data(self, data):
        if self.stack and not self.ignore:
            self.stack[-1].children.append(data)


def _visible(node):
    return (
        node.tag not in {"script", "style", "nav", "aside", "footer", "svg", "template"}
        and node.attrs.get("aria-hidden") != "true"
        and "hidden" not in node.attrs
        and not (node.tag == "section" and node.attrs.get("id"))
    )


def _descendants(node):
    for child in node.children:
        if isinstance(child, _Node) and _visible(child):
            yield child
            yield from _descendants(child)


def _plain(node):
    return "".join(
        c if isinstance(c, str) else _plain(c) for c in node.children if isinstance(c, str) or _visible(c)
    )


def _heading(node):
    heading = next((c for c in _descendants(node) if c.tag in {"h1", "h2"}), None)
    if heading is None:
        raise ValueError("Reference section has no heading")
    return heading, " ".join(_plain(heading).split())


def _render(node, heading, url):
    if node is heading:
        return ""
    if node.tag == "button" and (
        node.attrs.get("role") != "tab" or node.attrs.get("aria-selected") != "true"
    ):
        return ""
    if node.tag == "pre":
        lines = [c for c in _descendants(node) if "code-line-content" in (c.attrs.get("class") or "").split()]
        code = "\n".join(_plain(line) for line in lines) if lines else _plain(node)
        fence = "`" * max(3, 1 + max(map(len, re.findall(r"`+", code)), default=0))
        return f"\n\n{fence}\n{code}" + ("" if code.endswith("\n") else "\n") + fence + "\n\n"
    body = "".join(
        re.sub(r"\s+", " ", c) if isinstance(c, str) else _render(c, heading, url)
        for c in node.children
        if isinstance(c, str) or _visible(c)
    )
    if node.tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        return "\n\n### " + body.strip() + "\n\n"
    if node.tag == "code":
        return "`" + body + "`"
    if node.tag == "a" and body.strip() and node.attrs.get("href"):
        target = urljoin(url, node.attrs["href"])
        if urlsplit(target).scheme in {"http", "https"}:
            return f"[{body}]({target})"
    if node.tag == "li":
        return "\n- " + body.strip() + "\n"
    if node.tag in {"p", "div", "ul", "ol", "table", "tr", "blockquote", "section"}:
        return "\n" + body.strip(" ") + "\n"
    if node.tag == "br":
        return "\n"
    if node.tag in {"span", "td", "th", "button"}:
        return " " + body + " "
    return body


def _compact(text):
    """Collapse layout spacing while preserving blank lines inside examples."""
    lines = []
    fence = ""
    for line in text.splitlines():
        if fence:
            lines.append(line)
            if line == fence:
                fence = ""
        elif re.fullmatch(r"`{3,}", line):
            fence = line
            lines.append(line)
        elif line.strip() or (lines and lines[-1]):
            lines.append(line.rstrip())
    return "\n".join(lines).strip()


class SectionReference:
    """Parse one aggregate once; every lookup checks both its family and its section."""

    def __init__(self, html: str):
        page = _Sections()
        page.feed(html)
        page.close()
        self.sections = page.ids

    def _one(self, slug):
        nodes = self.sections.get(slug, [])
        if len(nodes) != 1 or not nodes[0].closed:
            raise ValueError("Reference section is missing, duplicate or truncated")
        return nodes[0]

    def markdown(self, url: str) -> str:
        m = SECTION_URL.fullmatch(url)
        if not m:
            raise ValueError("Expected an official section reference URL")
        family, slug = m.groups()
        expected = "Supabase CLI" if family == "cli" else "Self-Hosting " + family.split("-")[-1].title()
        if _heading(self._one("introduction"))[1] != expected:
            raise ValueError("Reference belongs to another family")
        section = self._one(slug)
        heading, title = _heading(section)
        key = re.sub("[^a-z0-9]+", "-", title.lower().replace("'", "").replace("’", "")).strip("-")
        if slug != "introduction" and key != slug:
            raise ValueError("Reference section ID and heading disagree")
        body = _compact(_render(section, heading, url))
        if not body:
            raise ValueError("Reference section contains no body")
        return f"# {title}\n\n{body}\n"


def section_markdown(html: str, url: str) -> str:
    return SectionReference(html).markdown(url)
