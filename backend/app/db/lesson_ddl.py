"""Immutable private lesson origins, deletable through learner wipe."""

LESSON_IMMUTABLE_GUARDS = {
    table: (
        f"CREATE TRIGGER {table}_no_update BEFORE UPDATE ON {table} "
        "BEGIN SELECT RAISE(ABORT, 'lesson promotion history is immutable'); END"
    )
    for table in ("lesson_promotion", "lesson_promotion_snapshot")
}
