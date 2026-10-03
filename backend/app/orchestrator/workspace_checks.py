"""Expose deterministic arithmetic separately from unverified generated guidance."""

from decimal import Decimal, localcontext
from fractions import Fraction

from app.kernel.arithmetic_checks import EqualityCheck, check_equalities
from app.kernel.bin_checks import BinCheck, check_bins
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


BIN_SCOPE = (
    "Conditional static analysis: this assumes pd.cut or pandas.cut refers to the unmodified "
    "pandas function and the call receives valid input. No notebook code was executed, "
    "no dataset values or library installation were checked, and no whole-answer grade is implied. "
    "Bin numbers below are one-based; they refer to the order of the supplied edges."
)


def bin_checks_for(body: PlaygroundRequest) -> list[BinCheck]:
    # A hint must not disclose the complete boundary solution.
    return check_bins(body.code) if body.intent != "hint" else []


def bin_summary(checks: list[BinCheck]) -> str:
    lines = ["Local bin-boundary check (conditional; not executed):", BIN_SCOPE]
    for check in checks:
        lines.append(
            f"Line {check.line}: right={check.right}, include_lowest={check.include_lowest}; "
            + "edges: "
            + ", ".join(check.edges)
            + "."
        )
        for index in range(len(check.edges) - 1):
            left = "[" if not check.right or (index == 0 and check.include_lowest) else "("
            right = "]" if check.right else ")"
            lines.append(
                f"- Bin {index + 1} is {left}{check.edges[index]}, {check.edges[index + 1]}{right}."
            )
        for edge, target in zip(check.edges, check.boundary_bins, strict=True):
            result = (
                f"bin {target + 1}" if target is not None else "outside the bins (missing result)"
            )
            lines.append(f"- Boundary {edge} maps to {result}.")
    return "\n".join(lines)


def disclose_bins(text: str, checks: list[BinCheck]) -> str:
    if not checks:
        return text
    return (
        bin_summary(checks)
        + "\n\nTutor explanation (model-generated; may contain errors or disagree with the check):\n\n"
        + text
    )
