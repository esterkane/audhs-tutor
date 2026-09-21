"""Office Open XML (docx / pptx / xlsx) and OpenDocument (odt / odp / ods) -> blocks, using only
`zipfile` + `xml.etree`. Word: paragraphs with heading styles, tables. PowerPoint: slides in
presentation order with title + body + speaker notes. Excel/Calc: one table block per sheet (capped).
Writer/Impress mirror that. Embedded images are not read here (see `vision.py` for image files)."""

import io
import re
import zipfile
from collections.abc import Iterable
from typing import Any
from xml.etree import ElementTree as ET

from app.knowledge.ingest.types import Block
from app.knowledge.ingest.xmlsafe import parse_xml

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
OT = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
OTABLE = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
ODRAW = "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}"
OPRES = "{urn:oasis:names:tc:opendocument:xmlns:presentation:1.0}"
OOFFICE = "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}"

MAX_TABLE_ROWS = 200
MAX_TABLE_CHARS = 12_000
_HEADING_STYLE = re.compile(r"(heading|berschrift|title|titel|caption)\s*(\d)?", re.I)

OFFICE_SUFFIXES = {".docx", ".pptx", ".xlsx", ".odt", ".odp", ".ods", ".docm", ".pptm", ".xlsm"}


class OfficeError(ValueError):
    pass


def _open(data: bytes) -> zipfile.ZipFile:
    try:
        return zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as e:
        raise OfficeError("not an Office/ODF zip container (a legacy binary file?)") from e


def _xml(z: zipfile.ZipFile, name: str) -> ET.Element | None:
    try:
        return parse_xml(z.read(name))
    except KeyError:
        return None
    except ET.ParseError as e:
        raise OfficeError(f"{name}: {e}") from e


def _rels(z: zipfile.ZipFile, name: str) -> dict[str, str]:
    root = _xml(z, name)
    if root is None:
        return {}
    return {r.attrib["Id"]: r.attrib["Target"] for r in root.iter(f"{REL}Relationship")}


def _rows_block(rows: Iterable[list[str]], heading: str | None) -> Block | None:
    lines: list[str] = []
    size = 0
    for cells in rows:
        if not any(c.strip() for c in cells):
            continue
        line = "| " + " | ".join(c.strip() for c in cells) + " |"
        lines.append(line)
        size += len(line) + 1
        if len(lines) >= MAX_TABLE_ROWS or size > MAX_TABLE_CHARS:
            lines.append("| … |")
            break
    return Block(text="\n".join(lines), kind="table", heading=heading) if lines else None


# ----------------------------------------------------------------------------- DOCX
def _w_text(p: ET.Element) -> str:
    parts: list[str] = []
    for node in p.iter():
        if node.tag == f"{W}t":
            parts.append(node.text or "")
        elif node.tag == f"{W}tab":
            parts.append("\t")
        elif node.tag in (f"{W}br", f"{W}cr"):
            parts.append("\n")
    return "".join(parts)


def _w_style(p: ET.Element) -> str:
    st = p.find(f"{W}pPr/{W}pStyle")
    return st.attrib.get(f"{W}val", "") if st is not None else ""


def docx_blocks(data: bytes) -> tuple[str | None, list[Block]]:
    z = _open(data)
    body = _xml(z, "word/document.xml")
    if body is None:
        raise OfficeError("word/document.xml missing")
    styles: dict[str, str] = {}
    sroot = _xml(z, "word/styles.xml")
    if sroot is not None:
        for st in sroot.iter(f"{W}style"):
            name = st.find(f"{W}name")
            if name is not None:
                styles[st.attrib.get(f"{W}styleId", "")] = name.attrib.get(f"{W}val", "")
    title: str | None = None
    heading: str | None = None
    blocks: list[Block] = []
    para: list[str] = []
    is_list_prev = False

    def flush() -> None:
        nonlocal para
        text = "\n".join(para).strip()
        para = []
        if text:
            blocks.append(Block(text=text, kind="prose", heading=heading))

    root = body.find(f"{W}body")
    for el in root if root is not None else body:
        if el.tag == f"{W}p":
            text = _w_text(el).strip()
            sid = _w_style(el)
            sname = styles.get(sid, sid)
            m = _HEADING_STYLE.match(sname) or _HEADING_STYLE.match(sid)
            if m and text:
                flush()
                if m.group(1).lower() in ("title", "titel") and title is None:
                    title = text
                elif m.group(1).lower() != "caption":
                    heading = text
                else:
                    para.append(text)
                continue
            is_list = el.find(f"{W}pPr/{W}numPr") is not None
            if not text:
                flush()
            elif is_list:
                if not is_list_prev:
                    flush()
                para.append(f"• {text}")
            else:
                flush()
                para.append(text)
            is_list_prev = is_list
        elif el.tag == f"{W}tbl":
            flush()
            rows = [
                [" ".join(_w_text(p) for p in tc.iter(f"{W}p")) for tc in tr.iter(f"{W}tc")]
                for tr in el.iter(f"{W}tr")
            ]
            b = _rows_block(rows, heading)
            if b:
                blocks.append(b)
    flush()
    return title, blocks


# ----------------------------------------------------------------------------- PPTX
def _a_paragraphs(shape: ET.Element) -> list[str]:
    out: list[str] = []
    for p in shape.iter(f"{A}p"):
        text = "".join(t.text or "" for t in p.iter() if t.tag in (f"{A}t",)).strip()
        if text:
            lvl = p.find(f"{A}pPr")
            indent = int(lvl.attrib.get("lvl", "0")) if lvl is not None else 0
            out.append(("  " * indent + "• " if indent or len(out) else "") + text)
    return out


def _slide_paths(z: zipfile.ZipFile) -> list[str]:
    pres = _xml(z, "ppt/presentation.xml")
    rels = _rels(z, "ppt/_rels/presentation.xml.rels")
    ordered: list[str] = []
    if pres is not None:
        for sld in pres.iter(f"{P}sldId"):
            target = rels.get(sld.attrib.get(f"{R}id", ""))
            if target:
                ordered.append("ppt/" + target.lstrip("/").removeprefix("ppt/"))
    if not ordered:
        names = [n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]
        ordered = sorted(names, key=lambda n: int(re.findall(r"\d+", n)[-1]))
    return ordered


def pptx_blocks(data: bytes) -> tuple[str | None, list[Block]]:
    z = _open(data)
    paths = _slide_paths(z)
    if not paths:
        raise OfficeError("no slides found")
    title: str | None = None
    blocks: list[Block] = []
    for n, path in enumerate(paths, 1):
        slide = _xml(z, path)
        if slide is None:
            continue
        slide_title: str | None = None
        body: list[str] = []
        for sp in slide.iter(f"{P}sp"):
            ph = sp.find(f"{P}nvSpPr/{P}nvPr/{P}ph")
            ph_type = ph.attrib.get("type", "body") if ph is not None else None
            if ph_type in ("sldNum", "dt", "ftr"):
                continue
            paras = _a_paragraphs(sp)
            if not paras:
                continue
            if ph_type in ("title", "ctrTitle") and slide_title is None:
                slide_title = " ".join(paras).lstrip("• ")
            else:
                body.extend(paras)
        for tbl in slide.iter(f"{A}tbl"):
            rows = [
                [" ".join(_a_paragraphs(tc)) for tc in tr.iter(f"{A}tc")]
                for tr in tbl.iter(f"{A}tr")
            ]
            b = _rows_block(rows, None)
            if b:
                body.append(b.text)
        notes = ""
        rel_name = path.replace("ppt/slides/", "ppt/slides/_rels/") + ".rels"
        for target in _rels(z, rel_name).values():
            if "notesSlide" in target:
                notes_root = _xml(
                    z, "ppt/" + target.lstrip("/").removeprefix("../").removeprefix("ppt/")
                )
                if notes_root is not None:
                    lines = [
                        ln
                        for sp in notes_root.iter(f"{P}sp")
                        if (ph := sp.find(f"{P}nvSpPr/{P}nvPr/{P}ph")) is None
                        or ph.attrib.get("type") not in ("sldNum", "sldImg")
                        for ln in _a_paragraphs(sp)
                    ]
                    notes = " ".join(ln.lstrip("• ") for ln in lines).strip()
        if title is None and slide_title:
            title = slide_title
        heading = f"Slide {n}" + (f": {slide_title}" if slide_title else "")
        text = "\n".join(body).strip()
        if notes:
            text = (text + "\n\n" if text else "") + f"Notes: {notes}"
        if text:
            blocks.append(Block(text=text, kind="slide", heading=heading))
    return title, blocks


# ----------------------------------------------------------------------------- XLSX
def _col_index(ref: str) -> int:
    letters = re.match(r"[A-Z]+", ref)
    idx = 0
    for ch in letters.group(0) if letters else "A":
        idx = idx * 26 + (ord(ch) - 64)
    return idx - 1


def xlsx_blocks(data: bytes) -> tuple[str | None, list[Block]]:
    z = _open(data)
    shared: list[str] = []
    sroot = _xml(z, "xl/sharedStrings.xml")
    if sroot is not None:
        shared = ["".join(t.text or "" for t in si.iter(f"{S}t")) for si in sroot.iter(f"{S}si")]
    wb = _xml(z, "xl/workbook.xml")
    rels = _rels(z, "xl/_rels/workbook.xml.rels")
    sheets: list[tuple[str, str]] = []
    if wb is not None:
        for sh in wb.iter(f"{S}sheet"):
            target = rels.get(sh.attrib.get(f"{R}id", ""), "")
            if target:
                sheets.append(
                    (sh.attrib.get("name", "Sheet"), "xl/" + target.lstrip("/").removeprefix("xl/"))
                )
    blocks: list[Block] = []
    for name, path in sheets:
        root = _xml(z, path)
        if root is None:
            continue
        rows: list[list[str]] = []
        for row in root.iter(f"{S}row"):
            cells: dict[int, str] = {}
            for c in row.iter(f"{S}c"):
                ci = _col_index(c.attrib.get("r", "A1"))
                t = c.attrib.get("t", "")
                v = c.find(f"{S}v")
                if t == "s" and v is not None and v.text is not None:
                    val = shared[int(v.text)] if int(v.text) < len(shared) else ""
                elif t == "inlineStr":
                    val = "".join(x.text or "" for x in c.iter(f"{S}t"))
                else:
                    val = v.text or "" if v is not None else ""
                cells[ci] = val
            if cells:
                width = max(cells) + 1
                rows.append([cells.get(i, "") for i in range(width)])
        b = _rows_block(rows, name)
        if b:
            blocks.append(b)
    return None, blocks


# ----------------------------------------------------------------------------- ODF
def _o_text(el: ET.Element) -> str:
    parts: list[str] = []
    for node in el.iter():
        if node.tag == f"{OT}s":
            parts.append(" " * int(node.attrib.get(f"{OT}c", "1")))
        elif node.tag == f"{OT}tab":
            parts.append("\t")
        elif node.tag == f"{OT}line-break":
            parts.append("\n")
        elif node.tag in (f"{OT}note", f"{OT}tracked-changes", f"{OOFFICE}annotation"):
            continue
        if node.text and node.tag not in (f"{OT}note-citation",):
            parts.append(node.text)
        if node is not el and node.tail:
            parts.append(node.tail)
    return re.sub(r"[ \t]+", " ", "".join(parts)).strip()


def _o_table_rows(tbl: ET.Element) -> list[list[str]]:
    rows: list[list[str]] = []
    for tr in tbl.iter(f"{OTABLE}table-row"):
        cells: list[str] = []
        for tc in tr:
            if tc.tag not in (f"{OTABLE}table-cell", f"{OTABLE}covered-table-cell"):
                continue
            rep = min(int(tc.attrib.get(f"{OTABLE}number-columns-repeated", "1")), 50)
            text = " ".join(_o_text(p) for p in tc.iter(f"{OT}p"))
            cells.extend([text] * (rep if text else 1))
        rows.append(cells)
    return rows


def odt_blocks(data: bytes) -> tuple[str | None, list[Block]]:
    z = _open(data)
    root = _xml(z, "content.xml")
    if root is None:
        raise OfficeError("content.xml missing")
    body = root.find(f"{OOFFICE}body/{OOFFICE}text")
    if body is None:
        raise OfficeError("no office:text body")
    title: str | None = None
    heading: str | None = None
    blocks: list[Block] = []

    def walk(parent: ET.Element) -> None:
        nonlocal title, heading
        for el in parent:
            if el.tag == f"{OT}h":
                text = _o_text(el)
                if text:
                    if (
                        title is None
                        and el.attrib.get(f"{OT}outline-level", "1") == "1"
                        and not blocks
                    ):
                        title = text
                    heading = text
            elif el.tag == f"{OT}p":
                text = _o_text(el)
                if text:
                    blocks.append(Block(text=text, kind="prose", heading=heading))
            elif el.tag == f"{OT}list":
                items = [f"• {_o_text(li)}" for li in el.iter(f"{OT}list-item") if _o_text(li)]
                if items:
                    blocks.append(Block(text="\n".join(items), kind="prose", heading=heading))
            elif el.tag == f"{OTABLE}table":
                b = _rows_block(_o_table_rows(el), heading)
                if b:
                    blocks.append(b)
            elif el.tag in (f"{OT}section", f"{OOFFICE}text"):
                walk(el)

    walk(body)
    return title, blocks


def odp_blocks(data: bytes) -> tuple[str | None, list[Block]]:
    z = _open(data)
    root = _xml(z, "content.xml")
    if root is None:
        raise OfficeError("content.xml missing")
    title: str | None = None
    blocks: list[Block] = []
    for n, page in enumerate(root.iter(f"{ODRAW}page"), 1):
        slide_title: str | None = None
        body: list[str] = []
        notes = ""
        for frame in page.iter(f"{ODRAW}frame"):
            klass = frame.attrib.get(f"{OPRES}class", "")
            in_notes = any(anc.tag == f"{OPRES}notes" for anc in _ancestors(page, frame))
            paras = [_o_text(p) for p in frame.iter(f"{OT}p") if _o_text(p)]
            if not paras:
                continue
            if in_notes or klass == "notes":
                notes = (notes + " " + " ".join(paras)).strip()
            elif klass in ("title", "subtitle") and slide_title is None:
                slide_title = " ".join(paras)
            elif klass == "page-number":
                continue
            else:
                body.extend(paras)
        if title is None and slide_title:
            title = slide_title
        heading = f"Slide {n}" + (f": {slide_title}" if slide_title else "")
        text = "\n".join(body).strip()
        if notes:
            text = (text + "\n\n" if text else "") + f"Notes: {notes}"
        if text:
            blocks.append(Block(text=text, kind="slide", heading=heading))
    if not blocks and root.find(f"{OOFFICE}body/{OOFFICE}presentation") is None:
        raise OfficeError("no presentation body")
    return title, blocks


def _ancestors(root: ET.Element, target: ET.Element) -> list[ET.Element]:
    parents: dict[ET.Element, ET.Element] = {c: p for p in root.iter() for c in p}
    out: list[ET.Element] = []
    node: ET.Element | None = target
    while node is not None and node in parents:
        node = parents[node]
        out.append(node)
    return out


def ods_blocks(data: bytes) -> tuple[str | None, list[Block]]:
    z = _open(data)
    root = _xml(z, "content.xml")
    if root is None:
        raise OfficeError("content.xml missing")
    blocks: list[Block] = []
    for tbl in root.iter(f"{OTABLE}table"):
        b = _rows_block(_o_table_rows(tbl), tbl.attrib.get(f"{OTABLE}name", "Sheet"))
        if b:
            blocks.append(b)
    return None, blocks


LOADERS: dict[str, Any] = {
    ".docx": docx_blocks,
    ".docm": docx_blocks,
    ".pptx": pptx_blocks,
    ".pptm": pptx_blocks,
    ".xlsx": xlsx_blocks,
    ".xlsm": xlsx_blocks,
    ".odt": odt_blocks,
    ".odp": odp_blocks,
    ".ods": ods_blocks,
}


def office_blocks(data: bytes, suffix: str) -> tuple[str | None, list[Block]]:
    fn = LOADERS.get(suffix.lower())
    if fn is None:
        raise OfficeError(f"unsupported office suffix {suffix}")
    result: tuple[str | None, list[Block]] = fn(data)
    return result
