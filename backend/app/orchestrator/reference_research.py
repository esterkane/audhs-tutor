"""Small reviewed reference reuse; unmatched/broader requests retain the model path."""

import re

from app.orchestrator.personas import TutorPresentation
from app.schemas.knowledge_authoring import ResearchQuestion, ResearchTutorAnswer

VERSION = "python.string-identity.v1"
URL = "https://docs.python.org/3.12/reference/datamodel.html#objects-values-and-types"
REFERENCE = (
    "Python 3.12 language reference — objects, values and types. " + URL + "\n"
    "Immutable results may reuse an existing object of the same type and value. "
    "Identity is distinct from value equality; immutability does not guarantee a fresh object."
)
EN = (
    "No. Built-in strings are immutable, but that alone does not guarantee a fresh object. "
    "A different string value requires a different object; a result of the same type and value "
    "may reuse an existing object. For built-in strings, `==` compares values and `is` compares "
    "identity. Reuse can depend on the implementation."
)
DE = (
    "Nein. Eingebaute Strings sind unveränderlich; daraus allein folgt kein neues Objekt. "
    "Ein anderer String-Wert erfordert ein anderes Objekt; bei gleichem Typ und Wert kann ein "
    "vorhandenes Objekt wiederverwendet werden. Bei eingebauten Strings vergleicht `==` Werte "
    "und `is` die Identität. Die Wiederverwendung kann von der Implementierung abhängen."
)


def answer(
    passage: str, question: ResearchQuestion, presentation: TutorPresentation
) -> ResearchTutorAnswer | None:
    if (
        len(passage) > 1800
        or "python" not in passage.casefold()
        or not re.search(r"\b(?:strings?|str|zeichenketten?)\b", passage.casefold())
        or re.search(r"\b(?:subclass|unterklasse|numpy)\b|__\w+__|\bclass\s", passage.casefold())
        or question.memory_ids
        or question.unresolved.strip()
    ):
        return None
    query = question.tutor_request.strip() or question.prompt.strip()
    if len(query) > 500:
        return None
    first, _, rest = re.sub(r"\s+", " ", query.casefold()).partition("?")
    first = first.rstrip(".")
    english = re.fullmatch(
        r"does (?:string )?immutability (?:guarantee|require|imply|mean) "
        r"a (?:fresh|new) (?:string )?object(?: identity)?(?: here| for strings)?",
        first,
    )
    german = re.fullmatch(
        r"(?:bedeutet|garantiert|erfordert) (?:string-)?unveränderlichkeit(?: hier)? "
        r"(?:immer )?(?:ein (?:neues|frisches) (?:string-)?objekt|eine neue objektidentität)",
        first,
    )
    permitted = {
        "",
        "explain equality and identity",
        "explain string equality versus identity",
        "distinguish == and is",
        "distinguish equal values from identity without predicting an unspecified runtime",
        "unterscheide == und is",
        "erkläre den unterschied zwischen == und is",
    }
    if not (english or german) or rest.strip().rstrip(".").replace("`", "") not in permitted:
        return None
    language = presentation.language
    if language == "unchanged":
        language = "de" if german else "en"
    return ResearchTutorAnswer(
        discussion=DE if language == "de" else EN, source_quotes=[passage, REFERENCE]
    )
