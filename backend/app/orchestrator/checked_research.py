"""Complete checked calculations, not a general source or model truth classifier."""

import json

from app.kernel.repetition_results import repetition_results
from app.orchestrator.personas import TutorPresentation
from app.schemas.knowledge_authoring import ResearchQuestion, ResearchTutorAnswer

VERSION = "python.string-repetition.v1"


def answer(
    passage: str, question: ResearchQuestion, presentation: TutorPresentation
) -> ResearchTutorAnswer | None:
    # A custom request, uncertainty or selected memory can ask for more than this
    # closed calculation. Preserve the existing model path for all of those.
    if (
        len(passage) > 1800
        or "python" not in passage.casefold()
        or question.tutor_request.strip()
        or question.unresolved.strip()
        or question.memory_ids
    ):
        return None
    result = repetition_results(passage, question.prompt)
    if result is None or len(json.dumps(result.context(), ensure_ascii=False)) > 1600:
        return None
    language = presentation.language
    if language == "unchanged":
        language = "de" if question.prompt.strip().casefold().startswith("was geben ") else "en"
    rule = (
        "Bei dieser Zeichenketten-Wiederholung gibt die ganze Zahl die Anzahl der Kopien an; "
        "null oder negative Anzahlen ergeben eine leere Zeichenkette."
        if language == "de"
        else "For this string repetition, the integer gives the number of copies; "
        "zero or negative counts give an empty string."
    )
    # Observable values and unchanged name only; no allocation, implementation
    # mechanism, learner-mistake origin or claim that the whole source is true.
    return ResearchTutorAnswer(
        discussion=f"{rule} {result.prose(language)}", source_quotes=[passage]
    )
