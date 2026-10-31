"""Bounded mathematical vectors: exact decimal dot products/rankings, approximate cosines."""

import math
import re
from dataclasses import dataclass
from fractions import Fraction

_NAME = r"[A-Za-z][A-Za-z0-9_]{0,15}"
_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]{1,2})?")


@dataclass(frozen=True)
class VectorScore:
    name: str
    dot: Fraction
    cosine: float | None
    cosine_order: tuple[int, Fraction] | None


def vectors(source: str) -> dict[str, tuple[Fraction, ...]] | None:
    if len(source) > 1800:
        return None
    lines = [line.strip() for line in source.splitlines() if line.strip()]
    if not lines or lines[0].casefold() not in {"vectors:", "vektoren:"}:
        return None
    if not 2 <= len(lines[1:]) <= 9:
        return None
    result: dict[str, tuple[Fraction, ...]] = {}
    for line in lines[1:]:
        match = re.fullmatch(rf"({_NAME})\s*=\s*\[([^\[\]]*)\]", line)
        if match is None or match[1] in result:
            return None
        tokens = [token.strip() for token in match[2].split(",")]
        if tokens and not tokens[-1]:
            tokens.pop()
        if not 1 <= len(tokens) <= 128:
            return None
        if any(len(t) > 32 or _NUMBER.fullmatch(t) is None for t in tokens):
            return None
        values = tuple(Fraction(token) for token in tokens)
        if any(abs(value) > 10**6 for value in values):
            return None
        result[match[1]] = values
    return result


def compare(source: str, query: str, candidates: list[str]) -> list[VectorScore] | None:
    values = vectors(source)
    if values is None or query not in values or not 1 <= len(candidates) <= 8:
        return None
    if len(set(candidates)) != len(candidates) or any(name not in values for name in candidates):
        return None
    q = values[query]
    if any(len(values[name]) != len(q) for name in candidates):
        return None
    qnorm2 = sum((x * x for x in q), Fraction())
    results = []
    for name in candidates:
        v = values[name]
        dot = sum((x * y for x, y in zip(q, v, strict=True)), Fraction())
        norm2 = sum((x * x for x in v), Fraction())
        cosine = None
        order = None
        if qnorm2 and norm2:
            cosine = float(dot) / math.sqrt(float(qnorm2)) / math.sqrt(float(norm2))
            cosine = max(-1.0, min(1.0, cosine))
            sign = (dot > 0) - (dot < 0)
            # Common positive query norm cancels. Square only after separating signs.
            order = (sign, sign * dot * dot / norm2)
        results.append(VectorScore(name, dot, cosine, order))
    return results
