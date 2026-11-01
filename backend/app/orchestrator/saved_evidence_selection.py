"""Literal record-reference resolution against the current session's validated observations."""

import re

from app.integrations.supabase_evidence import StoredExperiment

NUMBERS = {
    word: number
    for number, words in enumerate(
        [
            ["zero", "null"],
            ["one", "eins", "ein", "eine", "einen"],
            ["two", "zwei"],
            ["three", "drei"],
            ["four", "vier"],
            ["five", "fünf"],
            ["six", "sechs"],
            ["seven", "sieben"],
            ["eight", "acht"],
            ["nine", "neun"],
            ["ten", "zehn"],
            ["eleven", "elf"],
            ["twelve", "zwölf"],
            ["thirteen", "dreizehn"],
            ["fourteen", "vierzehn"],
            ["fifteen", "fünfzehn"],
            ["sixteen", "sechzehn"],
            ["seventeen", "siebzehn"],
            ["eighteen", "achtzehn"],
            ["nineteen", "neunzehn"],
            ["twenty", "zwanzig"],
        ]
    )
    for word in words
}
NUMBER = r"(?:[0-9]{1,2}|" + "|".join(sorted(NUMBERS, key=len, reverse=True)) + r")"


def _number(word: str) -> int:
    return int(word) if word.isdigit() else NUMBERS[word]


def _resolve_quote(
    quote: str, records: tuple[StoredExperiment, ...], last_ordinal: int
) -> set[str]:
    direct = {r.source.id for r in records if r.source.id in quote}
    lower = quote.casefold()
    if re.search(r"[0-9]+\.[0-9]+|(?:minimum|min|workers|rows)\s*[:=]?\s*-\s*[0-9]", lower):
        return set()
    constraints: dict[str, int] = {}

    def add(key: str, value: int) -> bool:
        if key in constraints and constraints[key] != value:
            return False
        constraints[key] = value
        return True

    for pattern, ordinal in [
        (r"first|earliest|erste[nrs]?", 1),
        (r"second|zweite[nrs]?", 2),
        (r"third|dritte[nrs]?", 3),
        (r"fourth|vierte[nrs]?", 4),
        (r"last|latest|letzte[nrs]?", last_ordinal),
    ]:
        if re.search(
            r"\b(?:"
            + pattern
            + r")(?:\s+(?:local|saved|recorded|lokale[nrs]?|gespeicherte[nrs]?)){0,2}"
            + r"\s+(?:experiment|trial|case|versuch|fall)\b",
            lower,
        ):
            if not add("ordinal", ordinal):
                return set()
    for match in re.finditer(r"\b(?:experiment|trial|versuch)\s*#?\s*([0-9]{1,2})\b", lower):
        if not add("ordinal", int(match[1])):
            return set()
    for match in re.finditer(
        r"\b(?:minimum|min)(?:_active)?\s*[-:=]?\s*(" + NUMBER + r")\b", lower
    ):
        if not add("minimum", _number(match[1])):
            return set()
    for match in re.finditer(
        r"\b("
        + NUMBER
        + r")\s+(?:active\s+|initially\s+active\s+|aktive[nrs]?\s+)?(?:workers|rows|kräfte|kräften|zeilen)\b",
        lower,
    ):
        if not add("workers", _number(match[1])):
            return set()
    if not constraints:
        return direct
    return {
        r.source.id
        for r in records
        if (not direct or r.source.id in direct)
        and all(getattr(r, key) == value for key, value in constraints.items())
    }


def source_choices(
    question: str, records: tuple[StoredExperiment, ...], *, last_ordinal: int
) -> list[str] | None:
    """Resolve explicit literal references ourselves; do not ask a model to invent quotes."""
    # SQL omission is a presentation constraint. Positive requests outside the report keep ordinary tutoring.
    known = {record.source.id for record in records}
    if any(
        identity not in known
        for identity in re.findall(r"\bexperiment[0-9]+-[0-9a-f]{12}\b", question)
    ):
        return None
    substantive = re.sub(
        r"\b(?:no|without)\s+SQL\b|\b(?:keine|ohne)\s+SQL(?:-Befehle)?", "", question, flags=re.I
    )
    if re.search(
        r"\b(?:RLS|JWT|SSI|migration|kubernetes|qdrant|supavisor|pricing|preise|production|produktion|polic(?:y|ies)|richtlinien?|socratic|sokratisch|SQL)\b",
        substantive,
        re.I,
    ):
        return None
    if re.search(
        r"\b(?:run|create|execute|install|start|write|implement)\b|was wäre|angenommen",
        substantive,
        re.I,
    ):
        return None
    divider = (
        r"\b(?:with|and|versus|vs|mit|und)\b|,\s*(?="
        r"(?:first|second|third|fourth|erste[nrs]?|zweite[nrs]?|dritte[nrs]?|vierte[nrs]?)(?:\s|$))"
    )
    boundaries = [0]
    spans = []
    for match in re.finditer(divider, question, re.I):
        spans.append((boundaries[-1], match.start()))
        boundaries.append(match.end())
    spans.append((boundaries[-1], len(question)))
    selected = []
    for start, end in spans:
        clause = question[start:end].strip()
        matched = _resolve_quote(clause, records, last_ordinal)
        if len(matched) == 1:
            identity = next(iter(matched))
            if identity not in selected:
                selected.append(identity)
        elif matched or re.search(
            r"\b(?:minimum|min|workers|rows|kräfte|kräften|zeilen)\b|\b(?:first|second|third|fourth|last|latest|erste[nrs]?|zweite[nrs]?|dritte[nrs]?|vierte[nrs]?|letzte[nrs]?)\s+(?:local\s+)?(?:experiment|trial|case|versuch|fall)\b",
            clause,
            re.I,
        ):
            return None
    return selected if 1 <= len(selected) <= 4 else None
