from pathlib import Path
from xml.etree.ElementTree import ParseError

import pytest

from app.knowledge.ingest.loaders import load_file


def test_xml_project_source_keeps_code_and_provenance(tmp_path: Path) -> None:
    p = tmp_path / "pom.xml"
    p.write_text("<project>\n<artifactId>example</artifactId>\n<version>1.0</version>\n</project>")
    doc = load_file(p, course="Synthetic course")
    assert doc.source_type == "code" and doc.course == "Synthetic course"
    assert "<artifactId>example</artifactId>" in doc.blocks[0].text
    assert "```xml" in doc.blocks[0].text


def test_xml_credentials_redacted_without_modifying_source(tmp_path: Path) -> None:
    p = tmp_path / "config.xml"
    source = (
        "<config><password>private-value</password>"
        '<property name="api_key" value="credential-value"/>'
        '<server token="bearer-value"/></config>'
    )
    p.write_text(source)
    doc = load_file(p)
    result = "\n".join(b.text for b in doc.blocks)
    assert all(v not in result for v in ("private-value", "credential-value", "bearer-value"))
    assert p.read_text() == source


@pytest.mark.parametrize(
    "source", ['<!DOCTYPE a [<!ENTITY x SYSTEM "file:///etc/passwd">]><a>&x;</a>', "<a>broken"]
)
def test_unsafe_or_malformed_xml_is_not_source(tmp_path: Path, source: str) -> None:
    p = tmp_path / "source.xml"
    p.write_text(source)
    with pytest.raises((ValueError, ParseError)):
        load_file(p)


def test_timed_xml_remains_transcript(tmp_path: Path) -> None:
    p = tmp_path / "caption.xml"
    p.write_text(
        '<tt xmlns="http://www.w3.org/ns/ttml"><body><div>'
        '<p begin="00:00:01.000" end="00:00:02.000">Hello</p></div></body></tt>'
    )
    doc = load_file(p)
    assert doc.source_type == "transcript"
    assert any("Hello" in b.text for b in doc.blocks)


def test_xml_child_pair_secret_is_redacted(tmp_path: Path) -> None:
    p = tmp_path / "config.xml"
    p.write_text(
        "<configuration><property><name>db.password</name><value>hidden-value</value></property></configuration>"
    )
    doc = load_file(p)
    assert "hidden-value" not in "".join(block.text for block in doc.blocks)
