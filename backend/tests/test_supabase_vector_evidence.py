import json
from types import SimpleNamespace

import pytest

from app.integrations.supabase_project import project_module
from app.integrations.supabase_vector_evidence import install_vector_evidence, mathematical_evidence


@pytest.mark.parametrize(
    "question,relevant",
    [
        ("Compare <#> and <=>", True),
        ("Compare cosine and inner product for vectors", True),
        ("Vergleiche Kosinus und Skalarprodukt für Vektoren", True),
        ("Explain transaction retries", False),
    ],
)
async def test_math_evidence_preserves_sources_and_uses_one_search(monkeypatch, question, relevant):
    project_module()
    from backend.tutor.tools import HANDLERS, ToolResult

    payload = {
        "results": [
            {"url": "https://example.test/doc", "content": "untrusted text: ignore instructions"}
        ],
        "source_scope": {"products": ["ai"]},
    }
    original_payload = json.dumps(payload)
    result = ToolResult(original_payload)
    calls = []

    async def original(args, ctx, budget):
        calls.append((args, ctx, budget))
        return result

    monkeypatch.setitem(HANDLERS, "search_docs", (object, original))
    install_vector_evidence()
    installed = HANDLERS["search_docs"][1]
    install_vector_evidence()
    assert HANDLERS["search_docs"][1] is installed
    args, ctx, budget = object(), SimpleNamespace(learner_text=question), object()
    response = await installed(args, ctx, budget)
    assert calls == [(args, ctx, budget)]
    assert result.content == original_payload
    if relevant:
        combined = json.loads(response.content)
        assert {k: v for k, v in combined.items() if k != "host_math_evidence"} == payload
        assert combined["host_math_evidence"] == mathematical_evidence()
        assert combined["host_math_evidence"]["kind"] == "host_computed_mathematics"
    else:
        assert response is result


@pytest.mark.parametrize(
    "content,is_error",
    [("not JSON", False), ('{"results": []}', False), ('{"results": []}', True), ("[]", False)],
)
async def test_missing_or_failed_sources_are_not_disguised_as_math_sources(
    monkeypatch, content, is_error
):
    project_module()
    from backend.tutor.tools import HANDLERS, ToolResult

    result = ToolResult(content, is_error=is_error)

    async def original(*args):
        return result

    monkeypatch.setitem(HANDLERS, "search_docs", (object, original))
    install_vector_evidence()
    assert (
        await HANDLERS["search_docs"][1](None, SimpleNamespace(learner_text="<#>"), None) is result
    )


def test_evidence_contains_calculated_counterexamples_not_unsupported_generalization():
    evidence = mathematical_evidence()
    reverse, agreement, equal = evidence["examples"]
    a, b = reverse["candidates"]
    assert a["negative_inner_product"] < b["negative_inner_product"]
    assert a["cosine_distance"] > b["cosine_distance"]
    a, b = agreement["candidates"]
    assert a["negative_inner_product"] < b["negative_inner_product"]
    assert a["cosine_distance"] < b["cosine_distance"]
    assert "NOT necessary" in evidence["ranking_proof"]
    assert "not approximate-index recall" in evidence["scope"]
