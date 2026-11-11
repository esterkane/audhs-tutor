"""Conservative scope for canonical Supabase SDK method citations."""

import re
from dataclasses import dataclass
from typing import Literal

Sdk = Literal["javascript", "python", "dart", "swift", "kotlin", "csharp"]
_NAMES = {
    "javascript": r"(?:javascript|js|supabase-js)",
    "python": r"(?:python|supabase-py)",
    "dart": r"(?:flutter\s+dart|dart)",
    "swift": "swift",
    "kotlin": "kotlin",
    "csharp": r"(?:c#|csharp)",
}
_METHOD = re.compile(
    r"https://supabase\.com/docs/reference/(javascript|python|dart|swift|kotlin|csharp)/"
    r"(?:(v\d+)/)?[a-z0-9-]+/?(?:#[^\s]*)?"
)
_CLIENT = r"(?:client|sdk|api|library|bibliothek)"

_CURRENT = r"(?:current|latest|unversioned|aktuell\w*)"


@dataclass(frozen=True)
class SdkScope:
    sdk: str
    editions: tuple[str, ...] = ()


def learner_sdk_scope(text: str) -> SdkScope | None:
    explicit_urls = list(_METHOD.finditer(text))
    sdk_names = set(m[1] for m in explicit_urls)
    for sdk, name in _NAMES.items():
        if re.search(rf"(?<!\w){name}(?!\w)", text, re.I):
            sdk_names.add(sdk)
    if len(sdk_names) != 1:
        return None
    sdk = sdk_names.pop()
    name = _NAMES[sdk]
    # A language mention alone can describe the user's environment, not an SDK question.
    if re.search(
        r"\b(?:postgres(?:ql)?|node(?:\.js)?|typescript|runtime|server|docker)\s+(?:v(?:ersion)?\s*)?\d",
        text,
        re.I,
    ):
        # A second independently versioned dependency can require its own non-SDK evidence.
        return None
    gap = r"[\s-]+"
    client = rf"(?<!\w){name}(?!\w)(?:{gap}{_CLIENT})?"
    indicator = rf"(?:{name}{gap}{_CLIENT}|{_CLIENT}\s+(?:for\s+|für\s+)?{name}|supabase[\s.-]+{name})"
    if not explicit_urls and not re.search(indicator, text, re.I):
        if not re.search(rf"\b{_CURRENT}\s+SDK\b", text, re.I):
            return None
    if re.search(
        rf"\b(?:not(?:\s+using)?|exclude|ignore|without|nicht|kein\w*)\s+(?:(?:the|den|das|die|current|supabase)\s+)*{name}(?!\w)",
        text,
        re.I,
    ):
        return None
    editions = set(m[2] or "unversioned" for m in explicit_urls)
    edition = rf"(?:{_CURRENT}|(?:v\s*|version\s+)\d{{1,3}}(?:\.\d{{1,3}}){{0,2}}(?!\d|\.\d))"
    connectors = (
        r"(?:,\s*(?:(?:and|und)\s+)?|(?:\s+(?:and|or|vs\.?|versus|to|with|against|und|oder|mit|von|zu)\s+))"
    )
    for pattern in (
        rf"{client}\s+(?P<first>{edition})",
        rf"(?P<first>{edition})\s+(?:of\s+the\s+)?(?:supabase\s+)?{client}",
        rf"(?P<first>{_CURRENT})\s+sdk\b",
    ):
        for match in re.finditer(pattern, text, re.I):

            def record(token):
                number = re.search(r"\d+(?:\.\d+)*", token)
                editions.add("v" + number[0] if number else "unversioned")

            record(match["first"])
            rest = text[match.end() :]
            while extra := re.match(rf"{connectors}(?:the\s+)?(?P<next>{edition})(?!\w)", rest, re.I):
                record(extra["next"])
                rest = rest[extra.end() :]
    if len(editions) > 4:
        return None
    return SdkScope(sdk, tuple(sorted(editions)))


def incompatible_reference(url: str, scope: SdkScope | None) -> bool:
    match = _METHOD.fullmatch(url)
    if match is None or scope is None:
        return False
    return match[1] != scope.sdk or bool(scope.editions and (match[2] or "unversioned") not in scope.editions)


def url_pattern(scope: SdkScope, edition: str | None) -> str:
    branch = "" if edition == "unversioned" else (re.escape(edition) + "/" if edition else "(v[0-9]+/)?")
    return rf"^https://supabase\.com/docs/reference/{scope.sdk}/{branch}[a-z0-9-]+/?$"
