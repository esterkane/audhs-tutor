"""Expose deterministic arithmetic separately from unverified generated guidance."""

from decimal import Decimal, localcontext
from fractions import Fraction

from app.kernel.arithmetic_checks import EqualityCheck, check_equalities
from app.schemas.playground import PlaygroundRequest

SCOPE = (
    "Only the listed literal equalities were checked, using exact arithmetic. "
    "This does not determine whether you endorsed them, whether the formula fits the task, "
    "or whether your whole answer, code or interpretation is correct. It is not a grade."
)


def checks_for(body: PlaygroundRequest) -> list[EqualityCheck]:
    # Hint-only assistance must never reveal a solved calculation from the answer draft.
    return (
        check_equalities(body.learner_answer)
        if body.learner_answer and body.intent != "hint"
        else []
    )


def _value(value: str) -> str:
    fraction = Fraction(value)
    denominator = fraction.denominator
    for factor in (2, 5):
        while denominator % factor == 0:
            denominator //= factor
    if denominator != 1 or fraction.denominator == 1:
        return value
    with localcontext() as context:
        context.prec = 50
        decimal = format(Decimal(fraction.numerator) / Decimal(fraction.denominator), "f")
    # Only short exact terminating decimals add useful readability; otherwise keep the fraction.
    return f"{value} ({decimal})" if len(decimal) <= 16 else value


def summary(checks: list[EqualityCheck]) -> str:
    lines = ["Local arithmetic check (not a grade):"]
    for check in checks:
        verdict = "holds exactly" if check.holds else "does not hold exactly"
        lines.append(
            f"- `{check.expression}` {verdict}. Left side: {_value(check.left)}; right side: {_value(check.right)}."
        )
    return "\n".join(lines) + "\n\n" + SCOPE


def disclose_arithmetic(text: str, checks: list[EqualityCheck]) -> str:
    if not checks:
        return text
    return (
        summary(checks)
        + "\n\nTutor explanation (model-generated; may contain errors or disagree with the check):\n\n"
        + text
    )
