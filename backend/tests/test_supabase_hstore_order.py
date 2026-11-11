from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.integrations.supabase_function_lookup import hstore_order_answer, hstore_order_request


@pytest.mark.parametrize(
    ("question", "kind"),
    [
        ("Which hstore function returns all keys in alphabetical order?", "sorted"),
        ("Welche hstore-Funktion gibt die Schlüssel alphabetisch zurück?", "sorted"),
        ("Which hstore function extracts keys in their original insertion order?", "input"),
        (
            "Welche hstore-Funktion liefert alle Schlüssel in der Reihenfolge ihrer Eingabe?",
            "input",
        ),
        ("Which hstore function returns keys in reverse alphabetical order?", None),
        ("Which hstore function returns all keys alphabetically and removes accents?", None),
        ("Which hstore function returns values in alphabetical order?", None),
        ("Which hstore function returns all keys in order?", None),
    ],
)
def test_complete_question_scope(question, kind):
    assert hstore_order_request(question) == kind


@pytest.mark.parametrize(
    "failure", ["definition", "ordering", "other_chapter", "other_edition", "none"]
)
def test_requires_both_manual_passages(failure):
    state = SimpleNamespace(mode="neutral", language="en", persona_on=False)
    texts = [
        "skeys ( hstore ) → setof text Extracts an hstore's keys as a set.",
        "The order of the pairs is not significant (and may not be reproduced on output).",
    ]
    hits = [
        dict(url="https://www.postgresql.org/docs/17/hstore.html", title=str(i), tier=2, content=v)
        for i, v in enumerate(texts)
    ]
    if failure == "definition":
        hits[0]["content"] = "skeys is a function"
    elif failure == "ordering":
        hits[1]["content"] = "order is important"
    elif failure == "other_chapter":
        hits[0]["url"] = hits[0]["url"].replace("hstore", "ltree")
    elif failure == "other_edition":
        hits[1]["url"] = hits[1]["url"].replace("/17/", "/18/")
    result = hstore_order_answer("question", "sorted", state, {}, Mock(), hits)
    if failure != "none":
        assert result is None
    else:
        assert result is not None and "ORDER BY k" in result.turn.text
        assert [c.n for c in result.turn.citations] == [1, 2]
