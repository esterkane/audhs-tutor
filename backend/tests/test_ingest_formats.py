"""ingest-formats slice: transcript formats, Office/ODF/EPUB (zip+XML built in-test), HTML, RTF,
LaTeX, source code with secret redaction, structured text, archives (safety + provenance),
capabilities route, mixed folder end to end."""

# ruff: noqa: E501  (XML fixtures are long by nature)

import io
import json
import tarfile
import zipfile
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChunkProvenance, Document
from app.knowledge.ingest.archives import (
    archive_stem,
    content_root,
    extract_archive,
    should_skip_relpath,
)
from app.knowledge.ingest.epub import epub_blocks
from app.knowledge.ingest.htmltext import html_blocks
from app.knowledge.ingest.latex import latex_blocks
from app.knowledge.ingest.loaders import (
    SkipFile,
    is_expensive,
    iter_source_files,
    load_file,
    source_type_for,
    split_number,
)
from app.knowledge.ingest.normalize import redact_secrets
from app.knowledge.ingest.office import (
    docx_blocks,
    odp_blocks,
    odt_blocks,
    pptx_blocks,
    xlsx_blocks,
)
from app.knowledge.ingest.rtf import rtf_to_text
from app.knowledge.ingest.service import ingest_path
from app.knowledge.ingest.sourcecode import code_blocks, language_for
from app.knowledge.ingest.structured_text import structured_blocks
from app.knowledge.ingest.transcripts import (
    ass_cues,
    flex_seconds,
    json_cues,
    sbv_cues,
    tabular_cues,
    timestamped_text_cues,
    transcript_cues,
    ttml_cues,
)
from app.knowledge.sqlite_hybrid import SqliteHybridRepository


# ----------------------------------------------------------------------------- fixture builders
def _zip(files: dict[str, bytes | str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data.encode() if isinstance(data, str) else data)
    return buf.getvalue()


W_NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def make_docx() -> bytes:
    body = f"""<?xml version="1.0"?>
<w:document {W_NS}><w:body>
<w:p><w:pPr><w:pStyle w:val="Title"/></w:pPr><w:r><w:t>Data Science Intro</w:t></w:r></w:p>
<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>What is data?</w:t></w:r></w:p>
<w:p><w:r><w:t xml:space="preserve">Data is </w:t></w:r><w:r><w:t>recorded observations.</w:t></w:r></w:p>
<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/></w:numPr></w:pPr><w:r><w:t>structured</w:t></w:r></w:p>
<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/></w:numPr></w:pPr><w:r><w:t>unstructured</w:t></w:r></w:p>
<w:p><w:pPr><w:pStyle w:val="berschrift2"/></w:pPr><w:r><w:t>Tabelle</w:t></w:r></w:p>
<w:tbl><w:tr><w:tc><w:p><w:r><w:t>type</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>example</w:t></w:r></w:p></w:tc></w:tr>
<w:tr><w:tc><w:p><w:r><w:t>numeric</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>42</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
</w:body></w:document>"""
    styles = f"""<?xml version="1.0"?><w:styles {W_NS}>
<w:style w:styleId="berschrift2"><w:name w:val="heading 2"/></w:style></w:styles>"""
    return _zip(
        {"word/document.xml": body, "word/styles.xml": styles, "[Content_Types].xml": "<x/>"}
    )


A_NS = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
P_NS = 'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
R_NS = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'


def _slide(title: str, bullets: list[str]) -> str:
    body = "".join(f"<a:p><a:r><a:t>{b}</a:t></a:r></a:p>" for b in bullets)
    return f"""<?xml version="1.0"?><p:sld {P_NS} {A_NS}><p:cSld><p:spTree>
<p:sp><p:nvSpPr><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr><p:txBody><a:p><a:r><a:t>{title}</a:t></a:r></a:p></p:txBody></p:sp>
<p:sp><p:nvSpPr><p:nvPr><p:ph type="body"/></p:nvPr></p:nvSpPr><p:txBody>{body}</p:txBody></p:sp>
<p:sp><p:nvSpPr><p:nvPr><p:ph type="sldNum"/></p:nvPr></p:nvSpPr><p:txBody><a:p><a:r><a:t>7</a:t></a:r></a:p></p:txBody></p:sp>
</p:spTree></p:cSld></p:sld>"""


def make_pptx() -> bytes:
    pres = f"""<?xml version="1.0"?><p:presentation {P_NS} {R_NS}><p:sldIdLst>
<p:sldId id="257" r:id="rId3"/><p:sldId id="256" r:id="rId2"/></p:sldIdLst></p:presentation>"""
    rels = """<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId2" Type="x" Target="slides/slide1.xml"/><Relationship Id="rId3" Type="x" Target="slides/slide2.xml"/></Relationships>"""
    slide2_rels = """<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="x" Target="../notesSlides/notesSlide2.xml"/></Relationships>"""
    notes = f"""<?xml version="1.0"?><p:notes {P_NS} {A_NS}><p:cSld><p:spTree>
<p:sp><p:nvSpPr><p:nvPr><p:ph type="body"/></p:nvPr></p:nvSpPr><p:txBody><a:p><a:r><a:t>Remind them about the scaling factor.</a:t></a:r></a:p></p:txBody></p:sp>
<p:sp><p:nvSpPr><p:nvPr><p:ph type="sldNum"/></p:nvPr></p:nvSpPr><p:txBody><a:p><a:r><a:t>2</a:t></a:r></a:p></p:txBody></p:sp>
</p:spTree></p:cSld></p:notes>"""
    return _zip(
        {
            "ppt/presentation.xml": pres,
            "ppt/_rels/presentation.xml.rels": rels,
            "ppt/slides/slide1.xml": _slide(
                "Softmax", ["Turns scores into weights", "Sums to one"]
            ),
            "ppt/slides/slide2.xml": _slide("Scaled dot-product", ["Divide by sqrt(d_k)"]),
            "ppt/slides/_rels/slide2.xml.rels": slide2_rels,
            "ppt/notesSlides/notesSlide2.xml": notes,
        }
    )


S_NS = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'


def make_xlsx() -> bytes:
    wb = f"""<?xml version="1.0"?><workbook {S_NS} {R_NS}><sheets><sheet name="Results" sheetId="1" r:id="rId1"/></sheets></workbook>"""
    rels = """<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="x" Target="worksheets/sheet1.xml"/></Relationships>"""
    ss = f"""<?xml version="1.0"?><sst {S_NS}><si><t>model</t></si><si><t>accuracy</t></si><si><t>bert-base</t></si></sst>"""
    sheet = f"""<?xml version="1.0"?><worksheet {S_NS}><sheetData>
<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>
<row r="2"><c r="A2" t="s"><v>2</v></c><c r="B2"><v>0.91</v></c></row>
</sheetData></worksheet>"""
    return _zip(
        {
            "xl/workbook.xml": wb,
            "xl/_rels/workbook.xml.rels": rels,
            "xl/sharedStrings.xml": ss,
            "xl/worksheets/sheet1.xml": sheet,
        }
    )


ODF_NS = (
    'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
    'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
    'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
    'xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" '
    'xmlns:presentation="urn:oasis:names:tc:opendocument:xmlns:presentation:1.0"'
)


def make_odt() -> bytes:
    content = f"""<?xml version="1.0"?><office:document-content {ODF_NS}><office:body><office:text>
<text:h text:outline-level="1">Gradient descent</text:h>
<text:p>Step<text:s text:c="2"/>size matters.</text:p>
<text:list><text:list-item><text:p>momentum</text:p></text:list-item><text:list-item><text:p>Adam</text:p></text:list-item></text:list>
<table:table><table:table-row><table:table-cell><text:p>lr</text:p></table:table-cell><table:table-cell><text:p>0.001</text:p></table:table-cell></table:table-row></table:table>
</office:text></office:body></office:document-content>"""
    return _zip({"content.xml": content, "mimetype": "application/vnd.oasis.opendocument.text"})


def make_odp() -> bytes:
    content = f"""<?xml version="1.0"?><office:document-content {ODF_NS}><office:body><office:presentation>
<draw:page draw:name="page1"><draw:frame presentation:class="title"><draw:text-box><text:p>KV cache</text:p></draw:text-box></draw:frame>
<draw:frame presentation:class="outline"><draw:text-box><text:p>Store keys and values</text:p><text:p>Reuse per token</text:p></draw:text-box></draw:frame>
<presentation:notes><draw:frame presentation:class="notes"><draw:text-box><text:p>Mention memory growth.</text:p></draw:text-box></draw:frame></presentation:notes>
</draw:page></office:presentation></office:body></office:document-content>"""
    return _zip({"content.xml": content})


def make_epub() -> bytes:
    container = """<?xml version="1.0"?><container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>"""
    opf = """<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" xmlns:dc="http://purl.org/dc/elements/1.1/" version="3.0">
<metadata><dc:title>Deep Learning Notes</dc:title></metadata>
<manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
<item id="c1" href="ch1.xhtml" media-type="application/xhtml+xml"/><item id="c2" href="ch2.xhtml" media-type="application/xhtml+xml"/></manifest>
<spine><itemref idref="nav"/><itemref idref="c2"/><itemref idref="c1"/></spine></package>"""
    ch1 = "<html><head><title>Chapter One</title></head><body><h1>Backprop</h1><p>Chain rule applied.</p></body></html>"
    ch2 = "<html><head><title>Chapter Two</title></head><body><p>No heading here.</p></body></html>"
    nav = "<html><body><nav><ol><li>Chapter One</li></ol></nav></body></html>"
    return _zip(
        {
            "META-INF/container.xml": container,
            "OEBPS/content.opf": opf,
            "OEBPS/ch1.xhtml": ch1,
            "OEBPS/ch2.xhtml": ch2,
            "OEBPS/nav.xhtml": nav,
        }
    )


# ----------------------------------------------------------------------------- transcripts
def test_flexible_timestamps() -> None:
    assert flex_seconds("00:01:02.500") == 62.5
    assert flex_seconds("1:02") == 62.0
    assert flex_seconds("0:00:01.50") == 1.5  # ASS centiseconds
    assert flex_seconds("00:00:01:15", frame_rate=30) == 1.5  # frames
    assert flex_seconds("12.5s") == 12.5 and flex_seconds("1500ms") == 1.5
    assert flex_seconds("90000t", tick_rate=10_000_000) == 0.009
    with pytest.raises(ValueError):
        flex_seconds("yesterday")


def test_sbv_ass_ttml_cues() -> None:
    sbv = "0:00:01.000,0:00:03.000\nHello there\n\n0:00:03.000,0:00:05.000\nGeneral Kenobi\n"
    assert [c.text for c in sbv_cues(sbv)] == ["Hello there", "General Kenobi"]
    ass = (
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        "Dialogue: 0,0:00:02.00,0:00:04.00,Default,,0,0,0,,{\\an8}Second, with comma\\NNext line\n"
        "Dialogue: 0,0:00:00.50,0:00:02.00,Default,,0,0,0,,First\n"
    )
    cues = ass_cues(ass)
    assert [c.text for c in cues] == ["First", "Second, with comma Next line"] and cues[
        0
    ].start == 0.5
    ttml = """<?xml version="1.0"?><tt xmlns="http://www.w3.org/ns/ttml" xml:lang="en"><body><div>
<p begin="00:00:01.000" end="00:00:02.000">One<br/>two</p><p begin="2.5s" dur="1s"><span>three</span></p>
</div></body></tt>"""
    cues = ttml_cues(ttml)
    assert [(c.text, c.start, c.end) for c in cues] == [("One two", 1.0, 2.0), ("three", 2.5, 3.5)]
    assert transcript_cues(ttml, ".xml") is not None and transcript_cues("<root/>", ".xml") is None


def test_json_and_tabular_transcripts() -> None:
    whisper = {
        "segments": [
            {"start": 0.0, "end": 2.0, "text": " Hi "},
            {"start": 2.0, "end": 4.0, "text": "there"},
        ]
    }
    assert [c.text for c in json_cues(whisper) or []] == ["Hi", "there"]
    json3 = {
        "events": [
            {"tStartMs": 1000, "dDurationMs": 2000, "segs": [{"utf8": "Hel"}, {"utf8": "lo"}]}
        ]
    }
    assert (
        json_cues(json3) == [c for c in json_cues(json3) or []]
        and json_cues(json3)[0].text == "Hello"
    )
    yt_api = [{"text": "a", "start": 1.0, "duration": 2.0}]
    assert json_cues(yt_api)[0].end == 3.0
    podcast = {"segments": [{"startTime": 1.5, "endTime": 2.5, "body": "pod"}]}
    assert json_cues(podcast)[0].text == "pod"
    assert json_cues({"a": 1}) is None and json_cues([{"no": "shape"}]) is None
    tsv = "start\tend\ttext\n0\t2000\tfirst\n2000\t4000\tsecond\n" + "\n".join(
        f"{40000 + i * 1000}\t{41000 + i * 1000}\tx{i}" for i in range(3)
    )
    cues = tabular_cues(tsv)
    assert cues is not None and cues[1].start == 2.0 and cues[1].end == 4.0  # ms detected
    csv_ = "start,duration,text\n0.0,1.5,hello\n1.5,1.5,world\n"
    cues = tabular_cues(csv_)
    assert cues is not None and cues[1].end == 3.0
    assert tabular_cues("name,value\nx,1\n") is None


def test_timestamped_text_vs_prose() -> None:
    otter = "Saru  0:12\nSo attention weights the values.\n\nTutor  0:40\nRight, by the softmax.\n\nSaru  1:05\nGot it.\n"
    cues = timestamped_text_cues(otter)
    assert (
        cues is not None and cues[0].text.startswith("Saru: So attention") and cues[0].end == 40.0
    )
    lead = "[00:00] intro\n[00:10] the query vector\n[00:25] the key vector\ncontinues here\n"
    cues = timestamped_text_cues(lead)
    assert cues is not None and cues[2].text == "the key vector continues here"
    prose = "This is a paragraph.\n\nAnother paragraph with 12:30 lunch mentioned once.\n\nThird.\n"
    assert timestamped_text_cues(prose) is None
    assert transcript_cues(prose, ".txt") is None


# ----------------------------------------------------------------------------- documents
def test_docx_headings_lists_tables() -> None:
    title, blocks = docx_blocks(make_docx())
    assert title == "Data Science Intro"
    assert (
        blocks[0].heading == "What is data?" and blocks[0].text == "Data is recorded observations."
    )
    assert blocks[1].text == "• structured\n• unstructured"
    table = blocks[-1]
    assert table.kind == "table" and table.heading == "Tabelle"  # localised heading style resolved
    assert "| numeric | 42 |" in table.text


def test_pptx_order_titles_notes() -> None:
    title, blocks = pptx_blocks(make_pptx())
    assert title == "Scaled dot-product"  # first slide in *presentation* order (rId3)
    assert [b.heading for b in blocks] == ["Slide 1: Scaled dot-product", "Slide 2: Softmax"]
    assert (
        blocks[0].kind == "slide"
        and "Notes: Remind them about the scaling factor." in blocks[0].text
    )
    assert "7" not in blocks[1].text  # slide-number placeholder dropped


def test_xlsx_odt_odp() -> None:
    _, blocks = xlsx_blocks(make_xlsx())
    assert blocks[0].kind == "table" and blocks[0].heading == "Results"
    assert blocks[0].text == "| model | accuracy |\n| bert-base | 0.91 |"
    title, blocks = odt_blocks(make_odt())
    assert title == "Gradient descent" and blocks[0].text == "Step size matters."
    assert blocks[1].text == "• momentum\n• Adam" and "| lr | 0.001 |" in blocks[2].text
    title, blocks = odp_blocks(make_odp())
    assert title == "KV cache" and blocks[0].heading == "Slide 1: KV cache"
    assert "Notes: Mention memory growth." in blocks[0].text and "Store keys" in blocks[0].text


def test_epub_spine_order_and_chapter_titles() -> None:
    title, blocks = epub_blocks(make_epub())
    assert title == "Deep Learning Notes"
    assert [b.heading for b in blocks] == ["Chapter Two", "Backprop"]  # spine order, nav skipped


def test_html_rtf_latex() -> None:
    html = """<html><head><title>Notes</title><style>p{}</style></head><body><nav>skip me</nav>
<h1>Attention</h1><p>Weights <b>values</b>.</p><ul><li>query</li><li>key</li></ul>
<pre>def f():\n    return 1</pre><table><tr><th>a</th><th>b</th></tr><tr><td>1</td><td>2</td></tr></table>
<script>alert(1)</script><img alt="diagram of heads"></body></html>"""
    title, blocks = html_blocks(html)
    assert title == "Notes" and "skip me" not in " ".join(b.text for b in blocks)
    assert blocks[0].text == "Weights values." and blocks[0].heading == "Attention"
    assert blocks[1].text == "• query" and blocks[2].text == "• key"
    assert blocks[3].kind == "code" and "def f():" in blocks[3].text
    assert blocks[4].kind == "table" and blocks[4].text == "| a | b |\n| 1 | 2 |"
    assert "[image: diagram of heads]" in blocks[5].text
    rtf = r"{\rtf1\ansi{\fonttbl{\f0 Arial;}}{\colortbl;\red0\green0\blue0;}\f0 Hello \b bold\b0 \'e9\par Second\u8364? line}"
    assert rtf_to_text(rtf) == "Hello boldé\nSecond€ line"  # the space after \\b0 is a delimiter
    tex = r"""\documentclass{article}\title{Notes on \textbf{Attention}}
\begin{document}\maketitle
\section{Scaling} % comment
We divide by $\sqrt{d_k}$~\cite{vaswani}. See Section~\ref{sec:x}.
\begin{lstlisting}
scores = q @ k.T / d_k ** 0.5
\end{lstlisting}
\subsection{Why}
Because \emph{variance} grows.
\end{document}"""
    title, blocks = latex_blocks(tex)
    assert title == "Notes on Attention"
    assert blocks[0].heading == "Scaling" and blocks[0].text.startswith(
        "We divide by $\\sqrt{d_k}$"
    )
    assert "cite" not in blocks[0].text and "ref" not in blocks[0].text
    assert blocks[1].kind == "code" and "scores = q @ k.T" in blocks[1].text
    assert blocks[2].heading == "Why" and blocks[2].text == "Because variance grows."


def test_structured_text_and_code() -> None:
    rst = "Title\n=====\n\nIntro paragraph.\n\nSection\n-------\n\nBody.\n"
    blocks = structured_blocks(rst)
    assert [(b.heading, b.text) for b in blocks] == [
        ("Title", "Intro paragraph."),
        ("Section", "Body."),
    ]
    org = "* Heading\nline one\nline two\n** Sub\nmore\n"
    assert [b.heading for b in structured_blocks(org)] == ["Heading", "Sub"]
    py = (
        "import os\nAPI_KEY = 'sk-abcdefghijklmnopqrstuvwxyz123456'\n\n\n"
        "@decorator\ndef first(x):\n    return x\n\n\nclass Second:\n    def m(self):\n        pass\n"
    )
    blocks = code_blocks(py, "python", filename="mod.py")
    assert all(b.kind == "code" and b.text.startswith("```python") for b in blocks)
    assert (
        blocks[0].heading == "first" and "@decorator" in blocks[0].text
    )  # decorator kept with def
    joined = "\n".join(b.text for b in blocks)
    assert "sk-abcdef" not in joined and "<redacted>" in joined
    assert language_for("Dockerfile") == "dockerfile" and language_for("package-lock.json") is None
    with pytest.raises(ValueError):
        code_blocks("x" * 2500, "javascript")
    assert redact_secrets("token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ12") == "token: <redacted>"
    assert redact_secrets("password = hunter2") == "password = hunter2"  # short: left alone
    # ordinary LLM-course code is not a secret
    for line in (
        "next_token = model.generate(input_ids)",
        "token = tokenizer.decode(ids)",
        "password = getpass.getpass()",
        "secret = settings.SECRET_KEY",
        "api_key = os.environ['OPENAI_API_KEY']",
    ):
        assert redact_secrets(line) == line, line
    assert redact_secrets('api_key = "sk_live_1234567890abcdefXYZ"') == 'api_key = "<redacted>"'
    assert redact_secrets("API_KEY=abcdefghijklmnopqrstuvwxyz1234") == "API_KEY=<redacted>"


# ----------------------------------------------------------------------------- archives
def test_archive_safety_and_root_descent(tmp_path: Path) -> None:
    zbytes = _zip(
        {
            "repo-main/README.md": "# Repo\n\nHello.",
            "repo-main/src/app.py": "def run():\n    pass\n",
            "repo-main/.env": "SECRET=1",
            "repo-main/.git/config": "x",
            "repo-main/node_modules/x/index.js": "x",
            "repo-main/inner.zip": b"PK",
            "../../evil.txt": "no",
            "repo-main/notes/id_rsa": "key",
        }
    )
    archive = tmp_path / "repo-main (2).zip"
    archive.write_bytes(zbytes)
    dest = tmp_path / "out"
    report = extract_archive(archive, dest)
    assert report.extracted == 2
    reasons = dict(report.skipped)
    assert reasons["repo-main/.env"] == "possible secret file"
    assert reasons["repo-main/notes/id_rsa"] == "possible secret file"
    assert reasons["repo-main/inner.zip"] == "nested archive"
    assert reasons["../../evil.txt"] == "unsafe path"
    assert reasons["repo-main/.git/config"] == "hidden or build folder"
    assert not (tmp_path / "evil.txt").exists()
    assert content_root(dest) == dest / "repo-main"
    assert archive_stem(archive) == "repo-main"
    assert should_skip_relpath("a/b/.hidden") == "dotfile" and should_skip_relpath("a/b.py") is None
    # tar with the same layout
    tbuf = io.BytesIO()
    with tarfile.open(fileobj=tbuf, mode="w:gz") as t:
        data = b"print(1)\n"
        info = tarfile.TarInfo("x/main.py")
        info.size = len(data)
        t.addfile(info, io.BytesIO(data))
    tar = tmp_path / "x.tar.gz"
    tar.write_bytes(tbuf.getvalue())
    assert extract_archive(tar, tmp_path / "out2").extracted == 1


async def test_archive_ingest_provenance_and_idempotency(
    db: AsyncSession, fake_repo: SqliteHybridRepository, tmp_path: Path
) -> None:
    root = tmp_path / "Udemy Resources"
    (root / "Course A" / "01 - Intro").mkdir(parents=True)
    # a repo download next to the course folders → its own course, sections from folders
    (root / "agents-main (2).zip").write_bytes(
        _zip(
            {
                "agents-main/1_foundations/1_lab1.py": "def lab():\n    return 1\n",
                "agents-main/1_foundations/README.md": "# Lab one\n\nRead this first.",
                "agents-main/.gitignore": "*.pyc",
            }
        )
    )
    # a zip inside a lecture folder → inherits course/section/lecture, labelled by member path
    lecture = root / "Course A" / "01 - Intro" / "Lecture 1-2 - 2. Setup"
    lecture.mkdir()
    (lecture / "code.zip").write_bytes(_zip({"setup/run.sh": "echo hi\n", "setup/.env": "K=1"}))
    report = await ingest_path(db, root, repo=fake_repo)
    by_uri = {r.uri: r for r in report.results}
    assert len(by_uri) == 3, report.skipped
    lab = next(r for u, r in by_uri.items() if u.endswith("!/1_foundations/1_lab1.py"))
    assert lab.course == "agents-main" and lab.source_type == "code"
    prov = (
        (
            await db.execute(
                select(ChunkProvenance).where(ChunkProvenance.source_id == lab.document_id)
            )
        )
        .scalars()
        .first()
    )
    assert prov and prov.section == "foundations" and prov.lecture == "lab1"
    run = next(r for u, r in by_uri.items() if u.endswith("code.zip!/setup/run.sh"))
    assert run.course == "Course A"
    prov = (
        (
            await db.execute(
                select(ChunkProvenance).where(ChunkProvenance.source_id == run.document_id)
            )
        )
        .scalars()
        .first()
    )
    assert prov and prov.section == "Intro" and prov.lecture == "Setup"
    assert any(
        s.path.endswith("code.zip!/setup/.env") and "secret" in s.reason for s in report.skipped
    )
    again = await ingest_path(db, root, repo=fake_repo)
    assert again.summary()["new_versions"] == 0 and again.summary()["unchanged"] == 3
    docs = (await db.execute(select(Document))).scalars().all()
    assert all("!/" in d.uri for d in docs)


# ----------------------------------------------------------------------------- dispatch + e2e
def test_source_types_and_walker(tmp_path: Path) -> None:
    assert (
        source_type_for(Path("x.docx")) == "document"
        and source_type_for(Path("x.pptx")) == "slides"
    )
    assert source_type_for(Path("x.mp3")) == "audio" and source_type_for(Path("x.mkv")) == "video"
    assert (
        source_type_for(Path("x.png")) == "image" and source_type_for(Path("Dockerfile")) == "code"
    )
    assert source_type_for(Path("x.rar")) is None
    assert source_type_for(Path("index.ts")) == "code"  # TypeScript, never MPEG-TS video
    assert (
        is_expensive(Path("a.mp3"))
        and is_expensive(Path("a.pdf"))
        and not is_expensive(Path("a.doc"))
    )
    assert split_number("1_foundations") == (1, "foundations") and split_number("2024report") == (
        None,
        "2024report",
    )
    for name in (
        "a.docx",
        "b.py",
        "manifest.json",
        ".DS_Store",
        "uv.lock",
        ".env",
        "c.rar",
        "d.zip",
        "node_modules/x.js",
        "e.mp3",
        "sub/.hidden/f.md",
        "Makefile",
        "package.json",
    ):
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x")
    names = {p.relative_to(tmp_path).as_posix() for p in iter_source_files(tmp_path)}
    assert names == {"a.docx", "b.py", "c.rar", "d.zip", "e.mp3", "Makefile"}


async def test_mixed_folder_end_to_end(
    db: AsyncSession, fake_repo: SqliteHybridRepository, tmp_path: Path
) -> None:
    sec = tmp_path / "Course M" / "03 - Formats"
    sec.mkdir(parents=True)
    (sec / "010 - Word.docx").write_bytes(make_docx())
    (sec / "011 - Deck.pptx").write_bytes(make_pptx())
    (sec / "012 - Sheet.xlsx").write_bytes(make_xlsx())
    (sec / "013 - Writer.odt").write_bytes(make_odt())
    (sec / "014 - Book.epub").write_bytes(make_epub())
    (sec / "015 - Page.html").write_text(
        "<html><title>P</title><body><h1>H</h1><p>Body text.</p></body></html>"
    )
    (sec / "016 - Talk.sbv").write_text(
        "0:00:01.000,0:00:03.000\nfirst cue\n\n0:00:03.000,0:00:06.000\nsecond cue\n"
    )
    (sec / "017 - Whisper.json").write_text(
        json.dumps({"segments": [{"start": 0, "end": 3, "text": "hello whisper"}]})
    )
    (sec / "018 - Links.json").write_text(
        json.dumps([{"title": "Paper", "url": "https://arxiv.org/abs/1706.03762"}])
    )
    (sec / "019 - Empty.json").write_text("[]")
    (sec / "020 - Data.json").write_text(json.dumps({"rows": [1, 2, 3]}))
    (sec / "021 - Notes.rst").write_text("Head\n====\n\nBody.\n")
    (sec / "022 - Script.py").write_text("def main():\n    print('hi')\n")
    (sec / "023 - Text.tex").write_text("\\section{S}\nHello \\textbf{tex}.\n")
    (sec / "024 - Doc.rtf").write_text(r"{\rtf1\ansi Plain rtf text.\par}")
    (sec / "025 - Table.csv").write_text("model,acc\nbert,0.9\n")
    (sec / "026 - Old.mobi").write_bytes(b"BOOKMOBI")
    report = await ingest_path(db, tmp_path, repo=fake_repo)
    types = {Path(r.uri).name: r.source_type for r in report.results}
    assert types == {
        "010 - Word.docx": "document",
        "011 - Deck.pptx": "slides",
        "012 - Sheet.xlsx": "document",
        "013 - Writer.odt": "document",
        "014 - Book.epub": "book",
        "015 - Page.html": "html",
        "016 - Talk.sbv": "transcript",
        "017 - Whisper.json": "transcript",
        "018 - Links.json": "text",
        "021 - Notes.rst": "text",
        "022 - Script.py": "code",
        "023 - Text.tex": "document",
        "024 - Doc.rtf": "document",
        "025 - Table.csv": "document",
    }
    skipped = {Path(s.path).name: s.reason for s in report.skipped}
    assert skipped["019 - Empty.json"] == "json: empty list"
    assert "not a transcript" in skipped["020 - Data.json"]
    assert "calibre" in skipped["026 - Old.mobi"]
    word = next(r for r in report.results if r.uri.endswith(".docx"))
    assert word.title == "Data Science Intro" and word.chunks >= 1
    talk = next(r for r in report.results if r.uri.endswith(".sbv"))
    prov = (
        (
            await db.execute(
                select(ChunkProvenance).where(ChunkProvenance.source_id == talk.document_id)
            )
        )
        .scalars()
        .first()
    )
    assert prov and prov.lecture == "Talk" and prov.section == "Formats"
    # "notes" alone matches half the fixture ("Deep Learning Notes", "Notes › Head"); ask for the
    # speaker note's own words so the ranking does not hinge on the fake embedder's hash buckets
    hits = (await fake_repo.search("Remind them scaling factor speaker notes", k=3)).hits
    assert any("Notes: Remind them" in h.chunk.text for h in hits)
    with pytest.raises(SkipFile):
        load_file(sec / "019 - Empty.json", root=tmp_path)


def test_markdown_leading_rule_is_not_front_matter() -> None:
    from app.knowledge.ingest.markdown import parse_markdown

    md = parse_markdown("---\n**Company** report\n---\n\n## Findings\n\nGrowth.\n")
    assert md.meta == {} and "Growth." in md.body
    real = parse_markdown("---\ntitle: T\n---\n\nBody.\n")
    assert real.title == "T"


async def test_capabilities_route(client: AsyncClient) -> None:
    r = await client.get("/api/corpus/capabilities")
    assert r.status_code == 200, r.text
    caps = r.json()
    assert ".docx" in caps["formats"]["documents"] and ".mp3" in caps["audio"]
    assert caps["stt"]["ready"] is False and "whisper-large-v3-turbo" in caps["stt"]["detail"]
    assert caps["vision"]["ready"] is False and "gemma3-12b" in caps["vision"]["detail"]
    assert caps["unsupported"][".rar"].startswith("extract")


def test_corrupt_office_and_member_caps(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.knowledge.ingest import archives
    from app.knowledge.ingest.office import OfficeError

    with pytest.raises(OfficeError):
        load_file(_write(tmp_path / "bad.pptx", b"PK"), root=tmp_path)
    monkeypatch.setattr(archives, "MAX_MEMBERS", 2)
    big = tmp_path / "many.zip"
    big.write_bytes(_zip({f"f{i}.txt": "x" for i in range(3)}))
    with pytest.raises(ValueError, match="members"):
        extract_archive(big, tmp_path / "out")
    monkeypatch.setattr(archives, "MAX_TOTAL_BYTES", 10)
    small = tmp_path / "small.zip"
    small.write_bytes(_zip({"a.txt": "x" * 20}))
    with pytest.raises(ValueError, match="extraction cap"):
        extract_archive(small, tmp_path / "out2")


def test_xml_with_dtd_is_refused() -> None:
    from app.knowledge.ingest.xmlsafe import UnsafeXml, parse_xml

    with pytest.raises(UnsafeXml):
        parse_xml('<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><x>&a;</x>')
    assert parse_xml("<x>ok</x>").text == "ok"


def _write(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    return path
