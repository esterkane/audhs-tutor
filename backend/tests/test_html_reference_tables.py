from app.knowledge.ingest.htmltext import html_blocks


def test_reference_table_keeps_rows_after_200_and_their_codes():
    rows = "".join(f"<tr><td>synthetic-{i}</td><td>condition-{i}</td></tr>" for i in range(250))
    source = "<h2>Error reference</h2><table><tr><th>Code</th><th>Condition</th></tr>" + rows
    source += "<tr><td>42501</td><td>insufficient_privilege</td></tr></table>"
    _, blocks = html_blocks(source)
    tables = [b for b in blocks if b.kind == "table"]
    assert len(tables) == 1
    assert len(tables[0].text.splitlines()) == 252
    assert tables[0].text.endswith("| 42501 | insufficient_privilege |")
    assert tables[0].heading == "Error reference"
