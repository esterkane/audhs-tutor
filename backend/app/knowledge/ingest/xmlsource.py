"""Non-transcript XML source, validated without fetching schemas or resolving entities."""

import re
from xml.etree import ElementTree as ET

from app.knowledge.ingest.sourcecode import code_blocks
from app.knowledge.ingest.types import Block
from app.knowledge.ingest.xmlsafe import parse_xml

_SECRET = re.compile(r"password|passwd|secret|token|api[_-]?key|private[_-]?key", re.I)


def xml_source_blocks(text: str) -> list[Block]:
    # Explicit refusal anywhere, including beyond xmlsafe's initial inspection window.
    if "<!DOCTYPE" in text or "<!ENTITY" in text:
        raise ValueError("XML source with DTD/entity declarations is not accepted")
    root = parse_xml(text)
    changed = False
    for element in root.iter():
        labels = [element.tag.rsplit("}", 1)[-1]]
        labels.extend(element.get(key, "") for key in ("name", "key", "id"))
        labels.extend(
            child.text or "" for child in element if child.tag.rsplit("}", 1)[-1] in {"name", "key"}
        )
        secret_element = any(_SECRET.search(label) for label in labels)
        if secret_element:
            if element.text and element.text.strip():
                element.text = "[redacted]"
                changed = True
            for child in list(element):
                element.remove(child)
                changed = True
        for key, value in list(element.attrib.items()):
            if _SECRET.search(key) or (secret_element and key not in {"name", "key", "id"}):
                if value:
                    element.set(key, "[redacted]")
                    changed = True
    sanitized = ET.tostring(root, encoding="unicode") if changed else text
    return code_blocks(sanitized, "xml")
