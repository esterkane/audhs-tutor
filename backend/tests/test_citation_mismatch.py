import pytest

from app.orchestrator.actions import cited_indices, has_unsupported_citation


@pytest.mark.parametrize(
    "text,count,unsupported",
    [
        ("A claim [1].", 0, True),
        ("Ambiguous list [1, 4].", 3, False),
        ("A claim [0].", 3, True),
        ("A claim [1, 3].", 3, False),
        ("No references.", 0, False),
        ("Training values: [15, 25, 35].", 1, False),
        ("Use `x[9]` here.", 0, False),
        ("```python\nx = [9]\n```\nA claim [1].", 1, False),
        ("~~~python\nx = [9]\n~~~", 0, False),
        ("```python\nx = [9]", 0, False),
    ],
)
def test_unsupported_prose_citations(text: str, count: int, unsupported: bool) -> None:
    assert has_unsupported_citation(text, count) is unsupported


@pytest.mark.parametrize(
    "text,expected",
    [
        ("```python\nvalues = [1]\n```", set()),
        ("Use `items[1]` and `[2, 3]`.", set()),
        ("~~~json\n[1, 2]\n~~~\nA source claim [3].", {3}),
        ("```python\nvalues = [1]\n```\nA source claim [2].", {2}),
        ("A source claim [1, 3].", {1, 3}),
        ("``literal `code` with [1]``; claim [2].", {2}),
        ("```python\nvalues = [1]", set()),
    ],
)
def test_cited_sources_exclude_code_literals(text: str, expected: set[int]) -> None:
    assert cited_indices(text, 3) == expected
