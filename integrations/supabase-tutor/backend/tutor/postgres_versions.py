"""PostgreSQL release references in learner requests and official manual URLs."""

import re

# PostgreSQL's numbered manual URLs identify the major release. A fetched date
# does not establish applicability to a different major or a specific patch.
_PG_VERSION = r"(?:9\.\d{1,2}|[1-9]\d)(?:\.\d{1,2})?"
_PG_SEP = r"\s*(?:,\s*(?:(?:and|und)\s+)?|/|\b(?:and|or|versus|vs\.?|und|oder|gegen)\s+)\s*"
_PG_REQUEST = re.compile(
    rf"\b(?:postgresql|postgres|pg)\s*[-:]?\s*(?:(?:versions?|versionen)\s*)?v?"
    rf"({_PG_VERSION}(?:{_PG_SEP}v?{_PG_VERSION})*)(?!\w|\.\d)", re.I
)
_PG_MANUAL = re.compile(r"https://www\.postgresql\.org/docs/([^/]+)/")


def major(version: str) -> str:
    parts = version.split(".")
    return ".".join(parts[:2]) if parts[0] == "9" else parts[0]


def requested_releases(text: str) -> list[str]:
    return list(dict.fromkeys(version for match in _PG_REQUEST.finditer(text)
                              for version in re.findall(_PG_VERSION, match[1])))


def requested_majors(text: str) -> list[str]:
    return list(dict.fromkeys(map(major, requested_releases(text))))


def manual_edition(url: str) -> str | None:
    match = _PG_MANUAL.match(url)
    return match[1] if match else None


def without_release_mentions(text: str) -> str:
    return _PG_REQUEST.sub("PostgreSQL", text).strip()
