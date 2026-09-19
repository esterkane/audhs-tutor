---
name: db-migration
description: Change the SQLite schema safely with Alembic — edit ORM models, autogenerate, review, upgrade, add export/wipe test. Use for any table or column change.
argument-hint: "[short-message]"
allowed-tools: Bash(make migrate *) Bash(uv run alembic *) Bash(sqlite3 *)
---
# DB migration: $ARGUMENTS

1. Edit ORM models in `backend/app/models/`. Keep `learning_event` append-only (no destructive change to it, ever).
2. `make migrate m="$ARGUMENTS"` (runs `alembic revision --autogenerate` then `alembic upgrade head` against `data/dev.db`).
3. Open the generated file in `backend/alembic/versions/` and review: SQLite needs `batch_alter_table` for ALTERs; check indexes; no data loss without an explicit data-migration step.
4. Update `docs/EVENT-SCHEMA.md` / `docs/ARCHITECTURE.md` data-model section if tables changed.
5. Run `backend/tests/test_export_wipe.py` and the full backend suite.
6. Commit migration + model + docs together.

Current heads: !`cd "${CLAUDE_PROJECT_DIR}/backend" 2>/dev/null && (uv run alembic heads 2>/dev/null || echo "alembic not initialised yet") || echo "backend not initialised yet"`
