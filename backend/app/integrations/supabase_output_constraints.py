"""Read-only output constraints, separate from reported database conditions."""

import re

NO_SQL_REQUEST = re.compile(
    r"\b(?:no|without|avoid|omit|skip)\s+(?:any\s+)?(?:sql|queries|commands|code)\b"
    r"|\b(?:do\s+not|don['’]t)\s+(?:show|write|include|propose|suggest|generate|invent)"
    r"\s+(?:any\s+)?(?:sql|queries|commands|code)\b"
    r"|\b(?:keine?|ohne)\s+(?:sql(?:[- ](?:abfragen|vorschläge|befehle))?|abfragen|befehle|code)\b",
    re.IGNORECASE,
)


def no_sql_requested(text: str) -> bool:
    return NO_SQL_REQUEST.search(text) is not None


def without_sql_output_restrictions(text: str) -> str:
    """For report-negation analysis only; never replace stored or model-facing text."""
    return NO_SQL_REQUEST.sub("", text)
