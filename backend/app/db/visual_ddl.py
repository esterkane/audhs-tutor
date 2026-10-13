"""Immutable visual content/receipts, with deletion available for learner wipe."""

VISUAL_IMMUTABLE_GUARDS = {
    table: (
        f"CREATE TRIGGER {table}_no_update BEFORE UPDATE ON {table} "
        "BEGIN SELECT RAISE(ABORT, 'authored visual history is immutable'); END"
    )
    for table in (
        "authored_visual_version",
        "authored_visual_source_snapshot",
        "authored_visual_review",
        "authored_visual_operation",
    )
}
