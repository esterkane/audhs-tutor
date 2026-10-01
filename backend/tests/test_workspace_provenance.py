import pytest

from app.orchestrator.workspace_provenance import WARNING, disclose


@pytest.mark.parametrize(
    "text",
    [
        "The supplied numbers give 60% [1].",
        "As stated [1, 2].",
    ],
)
def test_marks_unsupported_references_without_rewriting_original(text: str) -> None:
    result, flagged = disclose(text)
    assert flagged
    assert result == WARNING + "\n\n" + text


@pytest.mark.parametrize(
    "text",
    [
        "Use values[1] to select the second value.",
        "Use `[1]` as a Python list.",
        "```python\n[1]\n```",
        "~~~python\n[1]\n~~~",
        "The rate is 60%.",
        "[1](https://example.invalid) is a link label.",
    ],
)
def test_preserves_code_and_plain_prose(text: str) -> None:
    assert disclose(text) == (text, False)
