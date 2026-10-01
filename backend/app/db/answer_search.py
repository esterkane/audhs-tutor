"""Local derived index: only the request label and completed answer, never code/history.

The authoritative tutor_answer row enforces learner ownership at query time. Triggers
keep this disposable index in the same transaction as insertion, replacement and wipe.
"""

import re

ANSWER_SEARCH_DDL = (
    "CREATE VIRTUAL TABLE tutor_answer_fts USING fts5(id UNINDEXED, request, answer)",
    "CREATE TRIGGER tutor_answer_fts_insert AFTER INSERT ON tutor_answer BEGIN "
    "INSERT INTO tutor_answer_fts(id, request, answer) VALUES (new.id, "
    "coalesce(json_extract(new.request_json, '$.text'), "
    "json_extract(new.request_json, '$.question'), ''), new.text); END",
    "CREATE TRIGGER tutor_answer_fts_delete AFTER DELETE ON tutor_answer BEGIN "
    "DELETE FROM tutor_answer_fts WHERE id=old.id; END",
    "CREATE TRIGGER tutor_answer_fts_update AFTER UPDATE ON tutor_answer BEGIN "
    "DELETE FROM tutor_answer_fts WHERE id=old.id; "
    "INSERT INTO tutor_answer_fts(id, request, answer) VALUES (new.id, "
    "coalesce(json_extract(new.request_json, '$.text'), "
    "json_extract(new.request_json, '$.question'), ''), new.text); END",
)
ANSWER_SEARCH_BACKFILL = (
    "INSERT INTO tutor_answer_fts(id, request, answer) SELECT id, "
    "coalesce(json_extract(request_json, '$.text'), "
    "json_extract(request_json, '$.question'), ''), text FROM tutor_answer"
)


def literal_query(query: str) -> str | None:
    """All entered words must occur; FTS operators and punctuation are not executable syntax."""
    words = re.findall(r"[^\W_]+", query, flags=re.UNICODE)
    return " AND ".join('"' + word + '"' for word in words) or None
