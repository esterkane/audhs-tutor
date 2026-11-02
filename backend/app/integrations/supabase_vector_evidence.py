"""Labelled local math evidence alongside, never in place of, retrieved documentation."""

import json
import re
from dataclasses import asdict
from functools import wraps
from typing import Any

from app.kernel.vector_metrics import vector_metrics


def relevant_vector_question(text: str) -> bool:
    return any(op in text for op in ("<->", "<=>", "<#>")) or bool(
        re.search(r"\b(?:vector|vektor|embedding)\w*\b", text, re.I)
        and re.search(
            r"cosin|kosin|inner product|inneres produkt|skalarprodukt|normaliz|normalis", text, re.I
        )
    )


def mathematical_evidence() -> dict[str, Any]:
    query = [1, 0]
    examples = []
    for name, candidates in [
        ("unequal_norms_can_reverse_rankings", [[2, 2], [1, 0]]),
        ("unequal_norms_can_also_agree", [[2, 0], [0, 1]]),
        ("equal_nonzero_norms_agree", [[3, 4], [5, 0]]),
    ]:
        examples.append(
            {
                "case": name,
                "query": query,
                "candidates": [
                    {"vector": candidate, **asdict(vector_metrics(query, candidate))}
                    for candidate in candidates
                ],
            }
        )
    return {
        "kind": "host_computed_mathematics",
        "method": "vector-metrics.v1",
        "provenance": (
            "Local finite-vector calculations with floating-point rounding; not a documentation "
            "quotation or database execution."
        ),
        "scope": (
            "A fixed nonzero query and nonzero candidates of matching dimensions; exact metric "
            "rankings, not approximate-index recall or query planner behavior."
        ),
        "definitions": {
            "dot": "sum(q_i * v_i)",
            "l2_squared": "norm(q)^2 + norm(v)^2 - 2*dot(q,v)",
            "cosine_similarity": "dot(q,v) / (norm(q)*norm(v))",
            "cosine_distance": "1 - cosine_similarity",
            "negative_inner_product": "-dot(q,v)",
        },
        "ranking_proof": (
            "For equal nonzero candidate norms and a fixed nonzero query, the cosine denominator is "
            "the same positive constant and the L2-squared norm terms are constant. Thus ascending "
            "L2, cosine distance and negative inner product have the same ranking, including ties. "
            "Equal candidate norms are sufficient, NOT necessary; unequal norms may agree or "
            "disagree. Zero-vector cosine is undefined."
        ),
        "examples": examples,
    }


def install_vector_evidence() -> None:
    from app.integrations.supabase_project import project_module

    project_module()
    from backend.tutor.tools import HANDLERS, ToolResult

    model, original = HANDLERS["search_docs"]
    if getattr(original, "_audhs_vector_evidence", False):
        return

    @wraps(original)
    async def searched(args: Any, ctx: Any, budget: Any) -> Any:
        result = await original(args, ctx, budget)
        if result.is_error or not relevant_vector_question(ctx.learner_text):
            return result
        try:
            payload = json.loads(result.content)
        except (TypeError, ValueError):
            return result
        if (
            not isinstance(payload, dict)
            or not isinstance(payload.get("results"), list)
            or not payload["results"]
        ):
            return result
        return ToolResult(
            json.dumps(
                {**payload, "host_math_evidence": mathematical_evidence()}, ensure_ascii=False
            )
        )

    searched.__dict__["_audhs_vector_evidence"] = True
    HANDLERS["search_docs"] = model, searched
