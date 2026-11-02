from types import SimpleNamespace

import pytest

from app.integrations.supabase_citation_display import align_reasoning_reference


def state(url="https://example.test/definitions", language="en"):
    return SimpleNamespace(
        model_dump=lambda **kwargs: {"language": language, "citations": [{"n": 3, "url": url}]}
    )


def test_reasoning_note_keeps_complete_text_and_matches_document_metadata():
    explanation = "Complete explanation with necessary qualifications. [3]\n\n"
    note = "These are mathematical deductions from definitions; the document does not state the theorem."
    raw = explanation + "### Sources\n3. " + note
    result = align_reasoning_reference(raw, state())
    assert result.startswith(explanation)
    assert "3. [Document reference](https://example.test/definitions)" in result
    assert result.endswith("Reasoning note: " + note)
    assert align_reasoning_reference(result, state()) == result


@pytest.mark.parametrize(
    "raw",
    [
        "3. A mathematical deduction.",
        "### Sources\n3. [Mathematical deductions](https://example.test/doc)",
        "### Sources\n3. Ordinary document title.",
        "```md\n### Sources\n3. Mathematical deduction.\n```",
        "### Sources\n```\n3. Mathematical deduction.\n```",
        "### Sources\n### Examples\n3. Mathematical deduction.",
        "### Sources\n4. Mathematical deduction.",
    ],
)
def test_unrelated_or_ambiguous_content_is_unchanged(raw):
    assert align_reasoning_reference(raw, state()) == raw


@pytest.mark.parametrize(
    "url",
    ["javascript:alert(1)", "https://[", "https://example.test/a(b)", "https://example.test/a b"],
)
def test_unsafe_markdown_urls_are_never_inserted(url):
    raw = "### Sources\n3. Mathematical deduction."
    assert align_reasoning_reference(raw, state(url)) == raw


def test_german_and_crlf_are_preserved():
    raw = "Erklärung.\r\n## Quellen\r\n3. Mathematische Folgerungen aus Definitionen.\r\n"
    result = align_reasoning_reference(raw, state(language="de"))
    assert "[Dokumentreferenz]" in result
    assert "Herleitungsnotiz: Mathematische Folgerungen aus Definitionen.\r\n" in result
    assert result.startswith("Erklärung.\r\n")


def test_fence_like_code_content_does_not_end_the_code_block():
    raw = "```md\n```python\n### Sources\n3. Mathematical deduction.\n```"
    assert align_reasoning_reference(raw, state()) == raw
