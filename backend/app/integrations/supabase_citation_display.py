"""Keep numbered document references distinct from a model's mathematical notes."""

import re
from typing import Any
from urllib.parse import urlsplit

_HEADING = re.compile(r"^#{1,6}\s+(?:sources|quellen)\s*#*\s*$", re.I)
_REASONING = re.compile(
    r"mathematical deductions?|mathematische[nr]? (?:folgerungen?|herleitungen?)", re.I
)
_ENTRY = re.compile(r"^( {0,3})([1-9][0-9]*)\.\s+(.+)$")


def align_reasoning_reference(text: str, state: Any) -> str:
    """Preserve all reasoning text; only align an explicit bibliography note's label.

    Unknown headings, fenced examples, document links and ambiguous entries are
    untouched. This formats existing metadata; it neither verifies nor invents sources.
    """
    metadata = state.model_dump(mode="json")
    sources = {item["n"]: item["url"] for item in metadata.get("citations", [])}
    german = metadata.get("language") == "de"
    lines = text.splitlines(keepends=True)
    output = []
    in_sources = False
    fence: str | None = None
    for line in lines:
        stripped = line.strip()
        fence_match = re.match(r"^(`{3,}|~{3,})", stripped)
        if fence_match:
            marker = fence_match[1]
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence) and stripped == marker:
                fence = None
            output.append(line)
            continue
        if fence is not None:
            output.append(line)
            continue
        if re.match(r"^#{1,6}\s", line):
            in_sources = bool(_HEADING.fullmatch(stripped))
        match = _ENTRY.fullmatch(line.rstrip("\r\n")) if in_sources else None
        if (
            match
            and _REASONING.search(match[3])
            and "http" not in match[3].lower()
            and "](" not in match[3]
        ):
            url = sources.get(int(match[2]))
            if isinstance(url, str) and not re.search(r"[\s()<>]", url):
                try:
                    parsed = urlsplit(url)
                except ValueError:
                    output.append(line)
                    continue
                if parsed.scheme in {"http", "https"} and parsed.netloc:
                    ending = "\r\n" if line.endswith("\r\n") else "\n"
                    label = "Dokumentreferenz" if german else "Document reference"
                    note = "Herleitungsnotiz" if german else "Reasoning note"
                    output.append(f"{match[1]}{match[2]}. [{label}]({url}){ending}{ending}")
                    output.append(f"{note}: {match[3]}" + (ending if line.endswith("\n") else ""))
                    continue
        output.append(line)
    return "".join(output)
