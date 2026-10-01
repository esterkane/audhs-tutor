"""Bounded local text extraction from draw.io pages; no renderer or network access."""

import base64
import binascii
import html
import zlib
from html.parser import HTMLParser
from urllib.parse import unquote
from xml.etree import ElementTree as ET

from app.knowledge.ingest.normalize import redact_secrets, strip_invisible
from app.knowledge.ingest.types import Block
from app.knowledge.ingest.xmlsafe import parse_xml

MAX_PAGE_BYTES = 2_000_000
MAX_TOTAL_BYTES = 10_000_000
MAX_PAGES = 200
MAX_CELLS = 20_000
MAX_OUTPUT = 1_000_000


class _LabelText(HTMLParser):
    """A label is not a document: headings are content, not section metadata."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "template"}:
            self.hidden.append(tag)
        elif not self.hidden and tag in {
            "br",
            "p",
            "div",
            "li",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
        }:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if self.hidden:
            if tag == self.hidden[-1]:
                self.hidden.pop()
        elif tag in {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def _xml(text: str) -> ET.Element:
    if "<!DOCTYPE" in text or "<!ENTITY" in text:
        raise ValueError("Diagram DTD/entity declarations are not accepted")
    try:
        return parse_xml(text)
    except ET.ParseError as exc:
        raise ValueError("Malformed diagram XML") from exc


def _decode(text: str) -> str:
    if len(text) > MAX_PAGE_BYTES:
        raise ValueError("Diagram compressed page exceeds size limit")
    try:
        raw = base64.b64decode("".join(text.split()), validate=True)
        decoder = zlib.decompressobj(-15)
        expanded = decoder.decompress(raw, MAX_PAGE_BYTES + 1)
        if len(expanded) > MAX_PAGE_BYTES or decoder.unconsumed_tail:
            raise ValueError("Diagram expanded page exceeds size limit")
        if not decoder.eof or decoder.unused_data:
            raise ValueError("Incomplete or trailing diagram compressed data")
        return unquote(expanded.decode("utf-8"), errors="strict")
    except (binascii.Error, zlib.error, UnicodeError) as exc:
        raise ValueError("Invalid compressed diagram page") from exc


def _label(value: str, *, is_html: bool = False) -> str:
    if len(value) > 20_000:
        raise ValueError("Diagram label exceeds size limit")
    if is_html:
        parser = _LabelText()
        parser.feed(value)
        parser.close()
        value = " ".join("".join(parser.parts).split())
    else:
        value = html.unescape(value)
    return redact_secrets(strip_invisible(value)).strip()


def _endpoint(labels: dict[str, str], identifier: str | None) -> str:
    return labels.get(identifier, "[unresolved endpoint]") if identifier else "[free endpoint]"


def _append(lines: list[str], text: str, size: int) -> int:
    size += len(text) + 1
    if size > MAX_OUTPUT:
        raise ValueError("Diagram extracted text exceeds size limit")
    lines.append(text)
    return size


def drawio_blocks(text: str) -> list[Block] | None:
    """None means unrelated XML. Recognizable but invalid diagrams fail explicitly."""
    root = _xml(text)
    if root.tag not in {"mxfile", "mxGraphModel"}:
        return None
    pages = list(root.findall("diagram")) if root.tag == "mxfile" else [root]
    if not pages or len(pages) > MAX_PAGES:
        raise ValueError("Diagram page count is empty or exceeds limit")
    blocks: list[Block] = []
    total_bytes = 0
    cells_seen = 0
    output_size = 0
    for ordinal, page in enumerate(pages, 1):
        graph = page if page.tag == "mxGraphModel" else page.find("mxGraphModel")
        if graph is None:
            decoded = _decode(page.text or "")
            size = len(decoded.encode("utf-8"))
            graph = _xml(decoded)
        else:
            size = len(ET.tostring(graph, encoding="utf-8"))
        total_bytes += size
        if size > MAX_PAGE_BYTES or total_bytes > MAX_TOTAL_BYTES:
            raise ValueError("Diagram XML exceeds size limit")
        if graph.tag != "mxGraphModel" or graph.find("root") is None:
            raise ValueError("Diagram page has no graph model/root")
        heading = _label(page.get("name", "")) or f"Diagram page {ordinal}"
        output_size += len(heading)
        parents = {child: parent for parent in graph.iter() for child in parent}
        cells = list(graph.iter("mxCell"))
        cells_seen += len(cells)
        if cells_seen > MAX_CELLS:
            raise ValueError("Diagram cell count exceeds limit")
        labels: dict[str, str] = {}
        edges: list[ET.Element] = []
        nodes: list[ET.Element] = []
        cell_labels: dict[ET.Element, str] = {}
        cell_ids: dict[ET.Element, str] = {}
        lines: list[str] = []
        for intro in [
            "Diagram text representation; visual layout, images and styling are omitted.",
            "Connector source/target are file endpoints, not inferred meaning or causality.",
        ]:
            output_size = _append(lines, intro, output_size)
        ids: set[str] = set()
        for cell in cells:
            parent = parents.get(cell)
            wrapper = (
                parent if parent is not None and parent.tag in {"object", "UserObject"} else None
            )
            identifier = cell.get("id", "") or (
                wrapper.get("id", "") if wrapper is not None else ""
            )
            if not identifier or identifier in ids:
                raise ValueError("Missing or duplicate diagram cell ID")
            ids.add(identifier)
            cell_ids[cell] = identifier
            value = cell.get("value", "")
            if wrapper is not None:
                value = wrapper.get("label", value)
            label = _label(value, is_html="html=1" in cell.get("style", "").split(";"))
            labels[identifier] = label or f"[unlabelled cell {_label(identifier)}]"
            cell_labels[cell] = label
            if cell.get("edge") == "1":
                edges.append(cell)
            elif label:
                nodes.append(cell)
        edge_ids = {cell_ids[edge] for edge in edges}
        attached: dict[str, list[str]] = {}
        for node in nodes:
            parent_id = node.get("parent", "")
            if parent_id in edge_ids:
                attached.setdefault(parent_id, []).append(cell_labels[node])
            else:
                output_size = _append(
                    lines, f"Label [{_label(cell_ids[node])}]: {cell_labels[node]}", output_size
                )
        for edge in edges:
            label = cell_labels[edge]
            edge_id = cell_ids[edge]
            extra = attached.get(edge_id, [])
            output_size = _append(
                lines,
                f"Connector [{_label(edge_id)}] source: {_endpoint(labels, edge.get('source'))}; "
                f"target: {_endpoint(labels, edge.get('target'))}"
                + (f"; label: {label}" if label else "")
                + (f"; attached labels: {' | '.join(extra)}" if extra else ""),
                output_size,
            )
        if len(lines) == 2:
            continue  # No readable labels/connections: honest no_content outcome.
        body = "\n".join(lines)
        blocks.append(Block(text=body, heading=heading))
    return blocks
