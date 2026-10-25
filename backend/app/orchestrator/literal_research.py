"""Complete local results for closed literal-expression questions; wider help uses the model."""

import re

from app.kernel.literal_results import literal_results
from app.orchestrator.personas import TutorPresentation
from app.schemas.knowledge_authoring import ResearchQuestion, ResearchTutorAnswer

VERSION = "python.literal-expression.v1"


def code(value: str) -> str:
    fence = "`" * (max((len(m[0]) for m in re.finditer(r"`+", value)), default=0) + 1)
    return f"{fence} {value} {fence}"


def answer(
    source: str, question: ResearchQuestion, presentation: TutorPresentation
) -> ResearchTutorAnswer | None:
    if question.tutor_request.strip() or question.unresolved.strip() or question.memory_ids:
        return None
    checked = literal_results(source, question.prompt)
    if checked is None:
        return None
    results, german = checked
    if presentation.language != "unchanged":
        german = presentation.language == "de"
    parts = []
    for result in results:
        if result.error:
            verb = "löst" if german else "raises"
            reason = (
                ("mit einem Null-Divisor" if german else "with a zero divisor")
                if result.value == "ZeroDivisionError"
                else (
                    f"für die Operanden {code(result.detail)}"
                    if german
                    else f"for operands {code(result.detail)}"
                )
            )
            parts.append(f"{code(result.expression)} {verb} {code(result.value)} {reason}")
        else:
            parts.append(
                f"{code(result.expression)} {'ergibt' if german else 'evaluates to'} {code(result.value)}"
            )
    text = "; ".join(parts) + "."
    if len(text) > 1800:
        return None
    return ResearchTutorAnswer(discussion=text, source_quotes=[source])
