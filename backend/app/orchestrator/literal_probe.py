"""Literal-only prediction questions: parse syntax, never evaluate code or infer facts."""

import ast
import io
import re
import tokenize
from collections.abc import AsyncGenerator
from typing import Literal

from app.models_ai.gateway import StreamHandle
from app.schemas.socratic import SocraticLessonProbe

VERSION = "literal-probe.v2"
_REQUEST = re.compile(
    r"(?:please\s+)?ask(?:\s+me)?\s+(?:one|a single)\s+(?:socratic\s+)?question"
    r"\s+about\s+`(?P<expression>[^`\n]{1,180})`"
    r"(?:,?\s+without\s+(?:giving|telling)(?:\s+me)?\s+(?:the\s+)?(?:answer|outcome))?\.?",
    re.IGNORECASE,
)


def from_request(text: str, *, language: str = "unchanged") -> SocraticLessonProbe | None:
    """Recognize a complete explicit request, not a quoted/negated fragment.

    Unrecognized wording, multiple snippets, statements and explanations go through
    the ordinary model route. Only the supplied expression is copied; no answer,
    variable value, source fact or instruction is inferred from it.
    """
    if len(text) > 400:
        return None
    match = _REQUEST.fullmatch(text.strip())
    if match is None:
        return None
    expression = match["expression"].strip()
    try:
        tree = ast.parse(expression, mode="eval")
        if any(
            token.type == tokenize.COMMENT
            for token in tokenize.generate_tokens(io.StringIO(expression).readline)
        ):
            return None
    except (SyntaxError, ValueError, RecursionError):
        return None
    if not isinstance(tree.body, (ast.BinOp, ast.UnaryOp, ast.Call, ast.Compare, ast.Subscript)):
        return None
    operation = "Auswerten von" if language == "de" else "evaluating"
    return SocraticLessonProbe(situation=f"{operation} `{expression}`", focus="outcome")


async def stream(
    probe: SocraticLessonProbe, handle: StreamHandle, *, language: Literal["en", "de"] = "en"
) -> AsyncGenerator[str, None]:
    # No model_call row or model identity: no model was invoked. The normal tutor
    # loop still records its trace, events, checkpoint and saved answer.
    handle.route = "template"
    handle.finish_reason = "stop"
    yield probe.render(language=language)
