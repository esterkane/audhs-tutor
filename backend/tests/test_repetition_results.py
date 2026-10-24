import pytest

from app.kernel.repetition_results import repetition_results

SOURCE = (
    "In Python, text = 'go'. text * -3 returns ''. text * 0 returns ''. text * 2 returns 'gogo'."
)
QUESTION = "What do text * -3, text * 0 and text * 2 return, and does text change?"


def test_all_requested_results_are_composed_with_original_preservation():
    result = repetition_results(SOURCE, QUESTION)
    assert result is not None
    assert result.context()["results"] == {"text * -3": "", "text * 0": "", "text * 2": "gogo"}
    assert result.initial == "go"
    assert "text * -3 = ''" in result.prose()
    assert "text * 2 = 'gogo'" in result.prose()
    assert "unchanged" in result.prose()


@pytest.mark.parametrize(
    "source",
    [
        "In Python, text = open('secret'). text * 2 returns something.",
        SOURCE + " text = 'changed'.",
        SOURCE + " text += 'changed'.",
        SOURCE + " del text",
        SOURCE + " for text in other: pass",
        SOURCE + " (text := 'other')",
        SOURCE + " text -= other",
        SOURCE + " eval('bad')",
        "if unknown: text = 'go'.",
        "In Python, text = ['go'].",
        "In Python, text = '" + "a" * 200 + "'.",
    ],
)
def test_ambiguous_executable_or_large_sources_defer_without_execution(source):
    assert repetition_results(source, QUESTION) is None


@pytest.mark.parametrize(
    "question",
    [
        "Why does this happen?",
        "What do text * 99 return, and does text change?",
        "What do text * 2, other * 2 return, and does text change?",
        "What do text * 2 return, and does text change? Also explain complexity.",
        "What do text * 2 + 1 return, and does text change?",
        "What do text * 2, text * 3, text * 4, text * 5 return, and does text change?",
    ],
)
def test_unsupported_or_extra_questions_keep_normal_tutor_path(question):
    assert repetition_results(SOURCE, question) is None


def test_string_contents_are_only_data_and_unicode_results_are_literal():
    result = repetition_results("In Python, text = 'é'.", QUESTION)
    assert result is not None and result.examples[-1][1] == "éé"


def test_composition_removes_only_exact_duplicated_invariance_not_other_explanation():
    result = repetition_results(SOURCE, QUESTION)
    assert result is not None
    rule = "Non-positive counts produce zero copies. The original string remains unchanged in all cases."
    answer = result.compose(rule)
    assert "zero copies" in answer and "text * 2 = 'gogo'" in answer
    assert answer.count("unchanged") == 1
    assert "The original string remains unchanged" in rule  # original model text untouched
    assert "Keep this distinct condition." in result.compose("Keep this distinct condition.")


def test_quoted_invariance_and_code_delimiters_are_preserved():
    result = repetition_results("In Python, text = '`x`'.", QUESTION)
    assert result is not None and "``" in result.prose()
    quoted = "The source says 'The original string remains unchanged.'"
    assert quoted in result.compose(quoted)


@pytest.mark.parametrize(
    "suffix",
    [
        " text //= 2",
        " text **= 2",
        " text <<= 1",
        " text >>= 1",
        " text @= other",
        " text: str = 'changed'",
        " text **=2",
    ],
)
def test_other_rebindings_defer(suffix):
    assert repetition_results(SOURCE + suffix, QUESTION) is None


def test_python_identifiers_remain_case_sensitive():
    assert repetition_results("In Python, Text = 'go'.", QUESTION) is None
    upper_question = QUESTION.replace("text", "Text")
    assert repetition_results(SOURCE, upper_question) is None
    assert repetition_results("In Python, Text = 'go'.", upper_question) is not None


@pytest.mark.parametrize("count", ["02", "-03", "+02", "٢", "０"])
def test_text_integer_conversion_must_not_bless_invalid_python_literals(count):
    question = f"What do text * {count} return, and does text change?"
    assert repetition_results(SOURCE, question) is None


@pytest.mark.parametrize("name", ["None", "True", "async", "__debug__", "a²"])
def test_illegal_assignment_names_defer(name):
    source = f"In Python, {name} = 'go'."
    question = f"What do {name} * 2 return, and does {name} change?"
    assert repetition_results(source, question) is None
