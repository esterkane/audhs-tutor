"""Bounded finite-vector calculations for auditable teaching evidence, not ANN search."""

import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class VectorMetrics:
    dot: float
    negative_inner_product: float
    l2: float
    cosine_similarity: float | None
    cosine_distance: float | None


def _vector(values: Sequence[float]) -> tuple[float, ...]:
    if not 1 <= len(values) <= 4096:
        raise ValueError("Use between 1 and 4096 coordinates")
    result = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Coordinates must be finite real numbers")
        try:
            coordinate = float(value)
        except OverflowError as error:
            raise ValueError("Coordinate outside supported numerical range") from error
        if not math.isfinite(coordinate) or abs(coordinate) > 1e100:
            raise ValueError("Coordinate outside supported numerical range")
        if coordinate != 0 and abs(coordinate) < 1e-100:
            raise ValueError("Coordinate outside supported numerical range")
        result.append(coordinate)
    return tuple(result)


def vector_metrics(query: Sequence[float], candidate: Sequence[float]) -> VectorMetrics:
    """Compute exact-search metric definitions with ordinary floating-point rounding.

    Cosine is undefined if either vector is zero. Reject unsupported dimensions or
    numeric ranges rather than fabricate a score. No database or index is queried.
    """
    q, v = _vector(query), _vector(candidate)
    if len(q) != len(v):
        raise ValueError("Query and candidate dimensions must match")
    dot = math.fsum(a * b for a, b in zip(q, v, strict=True))
    l2 = math.hypot(*(a - b for a, b in zip(q, v, strict=True)))
    denominator = math.hypot(*q) * math.hypot(*v)
    cosine = max(-1.0, min(1.0, dot / denominator)) if denominator else None
    return VectorMetrics(dot, -dot, l2, cosine, None if cosine is None else 1.0 - cosine)
