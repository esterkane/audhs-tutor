import pytest

from backend.tutor.sdk_scope import row_page_query


@pytest.mark.parametrize(
    ("text", "should_expand"),
    [
        (
            "With version 0 of the Supabase C# client, how do I request just the second page of ten records?",
            True,
        ),
        ("Python SDK: load page 3 from my table.", True),
        ("Mit dem Swift-Client: Wie bekomme ich die dritte Seite mit zehn Zeilen?", True),
        ("How many records match my table?", False),
        ("How do I request the second page of auth users?", False),
        ("How do I request the next page of table rows with a cursor?", False),
        ("How do I display the next page of records without offset pagination?", False),
    ],
)
def test_scoped_numbered_table_paging(text, should_expand):
    assert (row_page_query("SDK pagination", text) != "SDK pagination") == should_expand
    assert row_page_query("create index", text) == "create index"
