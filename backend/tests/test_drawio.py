import base64
import zlib
from pathlib import Path
from urllib.parse import quote

import pytest

from app.knowledge.ingest.loaders import load_file

GRAPH = (
    '<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
    '<mxCell id="a" vertex="1" value="Input &amp;lt;T&amp;gt;"/>'
    '<mxCell id="b" vertex="1" value="&lt;b&gt;Output&lt;/b&gt;" style="html=1;"/>'
    '<mxCell id="e" edge="1" source="a" target="b" value="transform"/>'
    "</root></mxGraphModel>"
)


def compressed(text: str) -> str:
    encoder = zlib.compressobj(wbits=-15)
    return base64.b64encode(encoder.compress(quote(text).encode()) + encoder.flush()).decode()


@pytest.mark.parametrize("suffix", [".xml", ".drawio"])
@pytest.mark.parametrize("encoded", [False, True])
def test_diagram_labels_connectors_and_provenance(
    tmp_path: Path, suffix: str, encoded: bool
) -> None:
    source = f'<mxfile><diagram name="Example">{compressed(GRAPH) if encoded else GRAPH}</diagram></mxfile>'
    p = tmp_path / ("diagram" + suffix)
    p.write_text(source)
    doc = load_file(p, course="Synthetic")
    assert doc.source_type == "document"
    assert doc.course == "Synthetic" and doc.uri == str(p)
    assert "Input <T>" in doc.text and "Output" in doc.text
    assert "source: Input <T>" in doc.text and "target: Output" in doc.text
    assert "transform" in doc.text and "not inferred meaning" in doc.text
    assert "<b>" not in doc.text and doc.blocks[0].heading == "Example"
    assert p.read_text() == source


@pytest.mark.parametrize(
    "payload", ["not-base64!", compressed("<broken>"), compressed("<!DOCTYPE x><mxGraphModel/>")]
)
def test_bad_compressed_page_fails_honestly(tmp_path: Path, payload: str) -> None:
    p = tmp_path / "bad.xml"
    p.write_text(f"<mxfile><diagram>{payload}</diagram></mxfile>")
    with pytest.raises(ValueError):
        load_file(p)


def test_wrapped_cells_and_unknown_or_free_endpoints(tmp_path: Path) -> None:
    p = tmp_path / "wrapped.drawio"
    p.write_text(
        '<mxGraphModel><root><object id="node" label="Wrapped label">'
        '<mxCell vertex="1"/></object><object id="edge" label="Wrapped connection">'
        '<mxCell edge="1" source="node" target="missing"/></object>'
        '<mxCell id="free" edge="1"/></root></mxGraphModel>'
    )
    doc = load_file(p)
    assert "source: Wrapped label; target: [unresolved endpoint]" in doc.text
    assert "label: Wrapped connection" in doc.text
    assert "[free endpoint]" in doc.text


def test_expansion_and_output_limits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.knowledge.ingest import drawio

    p = tmp_path / "oversized.drawio"
    p.write_text(f"<mxfile><diagram>{compressed('x' * 5000)}</diagram></mxfile>")
    monkeypatch.setattr(drawio, "MAX_PAGE_BYTES", 1000)
    with pytest.raises(ValueError, match="expanded page"):
        load_file(p)
    p.write_text(GRAPH)
    monkeypatch.setattr(drawio, "MAX_OUTPUT", 100)
    with pytest.raises(ValueError, match="extracted text"):
        load_file(p)


def test_page_limits_duplicate_ids_and_empty_graph(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.knowledge.ingest import drawio

    p = tmp_path / "diagram.drawio"
    p.write_text("<mxfile><diagram/><diagram/></mxfile>")
    monkeypatch.setattr(drawio, "MAX_PAGES", 1)
    with pytest.raises(ValueError, match="page count"):
        load_file(p)
    p.write_text('<mxGraphModel><root><mxCell id="a"/><mxCell id="a"/></root></mxGraphModel>')
    with pytest.raises(ValueError, match="duplicate"):
        load_file(p)
    p.write_text('<mxGraphModel><root><mxCell id="a"/></root></mxGraphModel>')
    assert load_file(p).blocks == []


def test_late_dtd_and_executable_html_are_not_interpreted(tmp_path: Path) -> None:
    p = tmp_path / "diagram.xml"
    p.write_text(" " * 70000 + "<!DOCTYPE x><mxGraphModel/>")
    with pytest.raises(ValueError, match="DTD"):
        load_file(p)
    p.write_text(
        '<mxGraphModel><root><mxCell id="a" vertex="1" style="html=1;" '
        'value="&lt;script&gt;evil()&lt;/script&gt;&lt;b&gt;Safe label&lt;/b&gt;"/>'
        "</root></mxGraphModel>"
    )
    assert "evil()" not in load_file(p).text
    assert "Safe label" in load_file(p).text


@pytest.mark.parametrize(
    "label,expected",
    [
        ("&lt;h1&gt;Essential concept&lt;/h1&gt;", "Essential concept"),
        ("&lt;h2&gt;Heading&lt;/h2&gt;&lt;p&gt;Details&lt;/p&gt;", "Heading Details"),
    ],
)
def test_html_heading_labels_are_content(tmp_path: Path, label: str, expected: str) -> None:
    p = tmp_path / "heading.drawio"
    p.write_text(
        f'<mxGraphModel><root><mxCell id="a" style="html=1;" value="{label}"/></root></mxGraphModel>'
    )
    assert expected in load_file(p).text


def test_separate_labels_stay_with_their_connector(tmp_path: Path) -> None:
    p = tmp_path / "edges.drawio"
    p.write_text(
        '<mxGraphModel><root><mxCell id="a" value="Request"/><mxCell id="b" value="Result"/>'
        '<mxCell id="e" edge="1" source="a" target="b"/>'
        '<mxCell id="f" edge="1" source="b" target="a"/>'
        '<mxCell id="el" vertex="1" parent="e" style="edgeLabel;html=1;" value="Only if approved"/>'
        '<mxCell id="fl" vertex="1" parent="f" style="edgeLabel;html=1;" value="Retry"/>'
        "</root></mxGraphModel>"
    )
    lines = load_file(p).text.splitlines()
    e = next(line for line in lines if line.startswith("Connector [e]"))
    f = next(line for line in lines if line.startswith("Connector [f]"))
    assert "Only if approved" in e and "Retry" not in e
    assert "Retry" in f and "Only if approved" not in f
