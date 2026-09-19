"""Hand-written DDL shared by the ORM `after_create` hook and Alembic migrations.

`learning_event` is append-only (docs/EVENT-SCHEMA.md). SQLite triggers make that a database
guarantee, not a convention. `wipe_learner` drops and recreates them inside one transaction.
"""

LEARNING_EVENT_GUARDS: dict[str, str] = {
    "learning_event_no_update": (
        "CREATE TRIGGER learning_event_no_update BEFORE UPDATE ON learning_event "
        "BEGIN SELECT RAISE(ABORT, 'learning_event is append-only'); END"
    ),
    "learning_event_no_delete": (
        "CREATE TRIGGER learning_event_no_delete BEFORE DELETE ON learning_event "
        "BEGIN SELECT RAISE(ABORT, 'learning_event is append-only'); END"
    ),
}


def drop_guard(name: str) -> str:
    return f"DROP TRIGGER IF EXISTS {name}"
