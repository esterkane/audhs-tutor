"""XML parsing for untrusted container members (Office, ODF, EPUB, TTML). The stdlib parser has
entity-expansion limits since 3.12, but DTDs are still processed; course files never need one, so
any `<!DOCTYPE` is refused, as is an oversized part."""

from xml.etree import ElementTree as ET

MAX_XML_BYTES = 50_000_000


class UnsafeXml(ValueError):
    pass


def parse_xml(data: bytes | str) -> ET.Element:
    raw = data.encode("utf-8", "replace") if isinstance(data, str) else data
    if len(raw) > MAX_XML_BYTES:
        raise UnsafeXml(f"XML part larger than {MAX_XML_BYTES // 1_000_000} MB")
    head = raw[:4096].lstrip()
    if b"<!DOCTYPE" in raw[:65536] or head.startswith(b"<!ENTITY"):
        raise UnsafeXml("XML with a DTD/entity declaration is not accepted")
    return ET.fromstring(raw)
