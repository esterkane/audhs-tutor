"""EPUB (2 and 3) -> blocks in spine order via `container.xml` → OPF → manifest/spine. The
navigation document and cover are skipped; each chapter is parsed with the HTML extractor so
headings inside chapters become concept boundaries."""

import io
import posixpath
import zipfile

from app.knowledge.ingest.htmltext import html_blocks
from app.knowledge.ingest.types import Block
from app.knowledge.ingest.xmlsafe import parse_xml

_CNT = "{urn:oasis:names:tc:opendocument:xmlns:container}"
_OPF = "{http://www.idpf.org/2007/opf}"
_DC = "{http://purl.org/dc/elements/1.1/}"
MAX_CHAPTERS = 500


class EpubError(ValueError):
    pass


def epub_blocks(data: bytes) -> tuple[str | None, list[Block]]:
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as e:
        raise EpubError("not an EPUB zip container") from e
    try:
        container = parse_xml(z.read("META-INF/container.xml"))
    except KeyError as e:
        raise EpubError("META-INF/container.xml missing") from e
    rootfile = container.find(f".//{_CNT}rootfile")
    if rootfile is None:
        raise EpubError("no rootfile in container.xml")
    opf_path = rootfile.attrib["full-path"]
    opf = parse_xml(z.read(opf_path))
    base = posixpath.dirname(opf_path)
    title_el = opf.find(f".//{_DC}title")
    title = (title_el.text or "").strip() if title_el is not None else None
    items: dict[str, tuple[str, str, str]] = {}
    for it in opf.iter(f"{_OPF}item"):
        items[it.attrib["id"]] = (
            it.attrib.get("href", ""),
            it.attrib.get("media-type", ""),
            it.attrib.get("properties", ""),
        )
    blocks: list[Block] = []
    chapters = 0
    for ref in opf.iter(f"{_OPF}itemref"):
        href, media, props = items.get(ref.attrib.get("idref", ""), ("", "", ""))
        if not href or "nav" in props.split() or "cover" in props.split():
            continue
        if media and "html" not in media and "xml" not in media:
            continue
        path = posixpath.normpath(posixpath.join(base, href.split("#", 1)[0]))
        try:
            raw = z.read(path).decode("utf-8", "replace")
        except KeyError:
            continue
        chapter_title, chapter_blocks = html_blocks(raw)
        if chapter_title and chapter_blocks and all(b.heading is None for b in chapter_blocks):
            for b in chapter_blocks:  # a chapter without inner headings: its <title> is the heading
                b.heading = chapter_title
        blocks.extend(chapter_blocks)
        chapters += 1
        if chapters >= MAX_CHAPTERS:
            break
    return title or None, blocks
