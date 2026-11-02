"""Complete numeric comparison of explicitly named source vectors; broader discussion stays modeled."""

import math
import re
from itertools import groupby

from app.kernel.vector_comparison import VectorScore, compare
from app.orchestrator.personas import TutorPresentation
from app.schemas.knowledge_authoring import ResearchQuestion, ResearchTutorAnswer

VERSION = "vector.dot-cosine.v1"
DISTANCE_VERSION = "vector.distances.v1"
_LABEL = r"`([A-Za-z][A-Za-z0-9_]{0,15})`"
_LIST = rf"{_LABEL}(?:(?:\s*,\s*(?:(?:and|und)\s+)?|\s+(?:and|und)\s+){_LABEL})*"


def question_vectors(question: str) -> tuple[str, list[str], bool] | None:
    if len(question) > 700:
        return None
    en = re.fullmatch(
        rf"Compare dot product and cosine similarity for query {_LABEL} (?:and|with) candidates ({_LIST})\.?",
        question.strip(),
        re.IGNORECASE,
    )
    de = re.fullmatch(
        rf"Vergleiche Skalarprodukt und Kosinusähnlichkeit für Anfragevektor {_LABEL} "
        rf"mit (?:den )?Kandidaten ({_LIST})\.?",
        question.strip(),
        re.IGNORECASE,
    )
    match = en or de
    if match is None:
        return None
    return match[1], re.findall(_LABEL, match[2]), de is not None


def order_text(scores: list[VectorScore], *, cosine: bool) -> str:
    # Group by exact rational rank keys, not rounded display values.
    if cosine:
        entries = [(s.cosine_order, s.name) for s in scores if s.cosine_order is not None]
        entries.sort(key=lambda entry: entry[0], reverse=True)
        return " > ".join(
            " = ".join(f"`{name}`" for _, name in group)
            for _, group in groupby(entries, key=lambda entry: entry[0])
        )
    ranked = sorted(scores, key=lambda s: s.dot, reverse=True)
    return " > ".join(
        " = ".join(f"`{s.name}`" for s in group)
        for _, group in groupby(ranked, key=lambda s: s.dot)
    )


def answer(
    source: str, question: ResearchQuestion, presentation: TutorPresentation
) -> ResearchTutorAnswer | None:
    if question.tutor_request.strip() or question.unresolved.strip() or question.memory_ids:
        return None
    distance = distance_question(question.prompt)
    parsed = distance or question_vectors(question.prompt)
    if parsed is None:
        return None
    query, names, german = parsed
    scores = compare(source, query, names)
    if scores is None:
        return None
    if presentation.language != "unchanged":
        german = presentation.language == "de"
    if distance is not None:
        return distance_answer(source, query, scores, german)
    parts = [f"{'Für Anfragevektor' if german else 'For query'} `{query}`:"]
    for score in scores:
        cosine = (
            f"≈ {score.cosine:.12g}"
            if score.cosine is not None
            else (
                "undefiniert (Anfrage oder Kandidat hat Länge null)"
                if german
                else "undefined (query or candidate has zero length)"
            )
        )
        parts.append(
            f"- `{score.name}`: {'Skalarprodukt' if german else 'dot product'} = `{score.dot}`; "
            f"{'Kosinusähnlichkeit' if german else 'cosine similarity'} {cosine}."
        )
    parts.append(
        f"{'Skalarprodukt-Reihenfolge (größter Wert zuerst)' if german else 'Dot-product order (largest first)'}: "
        f"{order_text(scores, cosine=False)}."
    )
    cosine_order = order_text(scores, cosine=True)
    if cosine_order:
        parts.append(
            f"{'Kosinus-Reihenfolge (größter Wert zuerst)' if german else 'Cosine order (largest first)'}: "
            f"{cosine_order}."
        )
    if any(score.cosine is None for score in scores):
        parts.append(
            "Für Kosinus müssen Anfrage und Kandidat von null verschieden sein; undefinierte Werte "
            "werden nicht eingeordnet."
            if german
            else "Cosine needs a nonzero query and candidate; undefined scores are not ranked."
        )
    parts.append(
        "Das Skalarprodukt ist die Summe der Komponentenprodukte. Kosinusähnlichkeit teilt "
        "durch beide von null verschiedenen Vektorlängen; das Skalarprodukt tut das nicht. Eine "
        "größere Länge allein garantiert kein größeres Skalarprodukt."
        if german
        else "Dot product sums the component products. Cosine similarity divides by both nonzero "
        "vector magnitudes; dot product does not. Greater magnitude alone does not guarantee a larger dot product."
    )
    parts.append(
        "Kosinuswerte sind gerundet; die Reihenfolge wird exakt verglichen."
        if german
        else "Cosine values are approximate; ranking comparisons are exact."
    )
    text = "\n".join(parts)
    if len(text) > 1800:
        return None
    return ResearchTutorAnswer(discussion=text, source_quotes=[source])


def distance_question(question: str) -> tuple[str, list[str], bool] | None:
    if len(question) > 700:
        return None
    patterns = [
        r"Compare L2 distance, cosine distance and negative inner product "
        rf"for query {_LABEL} with candidates ({_LIST})\.?",
        r"Vergleiche L2-Abstand, Kosinusdistanz und negatives Skalarprodukt "
        rf"für Anfragevektor {_LABEL} mit (?:den )?Kandidaten ({_LIST})\.?",
    ]
    for german, pattern in enumerate(patterns):
        match = re.fullmatch(pattern, question.strip(), re.IGNORECASE)
        if match:
            return match[1], re.findall(_LABEL, match[2]), bool(german)
    return None


def distance_order(scores: list[VectorScore], metric: str) -> str:
    if metric == "cosine":
        # Ascending cosine distance is descending cosine similarity, including ties.
        return order_text(scores, cosine=True).replace(" > ", " < ")
    if metric == "negative_dot":
        return order_text(scores, cosine=False).replace(" > ", " < ")
    ranked = sorted(scores, key=lambda row: row.l2_squared)
    return " < ".join(
        " = ".join(f"`{row.name}`" for row in group)
        for _, group in groupby(ranked, key=lambda row: row.l2_squared)
    )


def distance_answer(
    source: str, query: str, scores: list[VectorScore], german: bool
) -> ResearchTutorAnswer | None:
    missing = "undefiniert" if german else "undefined"
    labels = (
        ("L2-Abstand", "Kosinusdistanz", "Negatives Skalarprodukt")
        if german
        else ("L2 distance", "Cosine distance", "Negative inner product")
    )
    parts = [f"{'Für Anfragevektor' if german else 'For query'} `{query}`:"]
    for row in scores:
        cosine = missing if row.cosine is None else f"≈ {1 - row.cosine:.12g}"
        parts.append(
            f"- `{row.name}`: {labels[0]} ≈ {math.sqrt(float(row.l2_squared)):.12g}; "
            f"{labels[1]} {cosine}; {labels[2]} = `{-row.dot}`."
        )
    parts.append(
        "Aufsteigend (kleinster Wert zuerst):" if german else "Ascending (smallest first):"
    )
    for label, metric in zip(labels, ("l2", "cosine", "negative_dot"), strict=True):
        parts.append(f"- {label}: {distance_order(scores, metric) or missing}.")
    parts.append(
        "L2 ist die Wurzel der Summe quadrierter Komponentendifferenzen. Kosinusdistanz ist "
        "1 minus Kosinusähnlichkeit. Das negative Skalarprodukt negiert die Summe der "
        "Komponentenprodukte: größere Skalarprodukte stehen aufsteigend zuerst; die Werte "
        "können negativ, null oder positiv sein."
        if german
        else "L2 is the square root of the sum of squared coordinate differences. Cosine distance is "
        "1 minus cosine similarity. Negative inner product negates the sum of coordinate products: "
        "ascending order puts larger inner products first; scores can be negative, zero or positive."
    )
    if any(row.cosine is None for row in scores):
        parts.append(
            "Kosinus ist bei einem Nullvektor undefiniert; diese Kandidaten werden nicht eingeordnet."
            if german
            else "Cosine is undefined for a zero vector; those candidates are not ranked."
        )
    parts.append(
        "Gerundete L2-/Kosinuswerte; exakte Rangvergleiche. Lokale Mathematik, keine Datenbankausführung."
        if german
        else "Rounded L2/cosine values; exact ranking comparisons. Local mathematics, not database execution."
    )
    text = "\n".join(parts)
    if len(text) > 1800:
        return None
    return ResearchTutorAnswer(discussion=text, source_quotes=[source])
