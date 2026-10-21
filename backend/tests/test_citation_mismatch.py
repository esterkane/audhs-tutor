import pytest

from app.orchestrator.actions import has_unsupported_citation


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
