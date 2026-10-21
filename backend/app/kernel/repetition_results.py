"""Bounded literal-string calculations. Never execute source code or instructions."""

import ast
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RepetitionResults:
    name: str
    initial: str
    examples: tuple[tuple[str, str], ...]

    def context(self) -> dict[str, object]:
        return {"name": self.name, "initial": self.initial, "results": dict(self.examples)}

    def prose(self) -> str:
        def code(value: str) -> str:
            fence = "`" * (max((len(m[0]) for m in re.finditer(r"`+", value)), default=0) + 1)
            return f"{fence}{value}{fence}"

        calculations = "; ".join(code(f"{expr} = {value!r}") for expr, value in self.examples)
        return (
            f"For {code(f'{self.name} = {self.initial!r}')}: {calculations}. "
            f"Repetition leaves {code(self.name)} unchanged."
        )

    def compose(self, rule: str) -> str:
        # Only exact standalone copies of the invariant supplied by prose() are removed.
        # Preserve every other explanation and the provider's original rule/history.
        for sentence in (
            "The original string remains unchanged in all cases.",
            "The original string remains unchanged in all cases [1].",
            "The original string remains unchanged.",
        ):
            rule = re.sub(r"(^|(?<=\. ))" + re.escape(sentence) + r"(?=\s|$)", "", rule)
        return f"{rule.strip()} {self.prose()}".strip()


def repetition_results(source: str, question: str) -> RepetitionResults | None:
    """Recognize only a direct output/original-state question about one literal string.

    Expressions, counts and initial string are bounded before multiplication. Ambiguous
    assignments, calls, mutation, control flow, extra questions and unknown syntax defer.
    """
    ask = re.fullmatch(
        r"what do (.+) return,? and does ([a-z_]\w{0,19}) change\??",
        question.strip(),
        re.IGNORECASE,
    )
    if not ask:
        return None
    name = ask[2]
    literal = r"(?:'(?:\\.|[^'\\\n])*'|\"(?:\\.|[^\"\\\n])*\")"
    declaration = re.match(
        rf"\s*(?:In Python,\s*)?{re.escape(name)}\s*=\s*({literal})\s*[.;\n]",
        source,
        re.IGNORECASE,
    )
    if not declaration or len(declaration[1]) > 128:
        return None
    if len(re.findall(rf"\b{re.escape(name)}\s*=", source)) != 1:
        return None
    remainder = source[declaration.end() :]
    if re.search(
        r"\b(?:if|for|while|def|class|lambda|import|exec|eval|del|globals|locals)\b", remainder
    ):
        return None
    if re.search(r"\b\w+\s*\(", remainder) or re.search(
        rf"\b{re.escape(name)}\s*(?:(?:\*\*|//|<<|>>|[-+*/%@|&^])=|:|\[|\.\w)", remainder
    ):
        return None
    try:
        initial = ast.literal_eval(declaration[1])
    except (ValueError, SyntaxError):
        return None
    if not isinstance(initial, str) or len(initial) > 32:
        return None
    expression = rf"\b{re.escape(name)}\s*\*\s*([+-]?\d{{1,2}})\b"
    matches = list(re.finditer(expression, ask[1]))
    if not 1 <= len(matches) <= 3:
        return None
    separators = re.sub(expression, "", ask[1])
    if re.sub(r"\band\b|[,\s]", "", separators, flags=re.IGNORECASE):
        return None
    examples: list[tuple[str, str]] = []
    for match in matches:
        count = int(match[1])
        if abs(count) > 8 or len(initial) * max(count, 0) > 128:
            return None
        examples.append((f"{name} * {count}", initial * count))
    result = RepetitionResults(name, initial, tuple(examples))
    if len({expr for expr, _ in examples}) != len(examples) or len(result.prose()) > 1600:
        return None
    return result
