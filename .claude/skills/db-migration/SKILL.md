---
name: db-migration
description: Change the SQLite schema safely with Alembic — edit ORM models, autogenerate, review, upgrade, add export/wipe test. Use for any table or column change.
argument-hint: "[short-message]"
allowed-tools: Bash(make migrate *) Bash(uv run alembic *) Bash(sqlite3 *)
---
# DB migration: $ARGUMENTS

1. Edit ORM models in `backend/app/db/models.py`. Keep `learning_event` append-only (no destructive change to it, ever).
2. `make migrate m="$ARGUMENTS"` — generates the revision only (`alembic revision --autogenerate`); it does **not** touch any database.
3. Open the generated file in `backend/alembic/versions/` and review: SQLite needs `batch_alter_table` for ALTERs, constraints must be **named**, NOT NULL columns need a server default; check indexes; no data loss without an explicit data-migration step.
3b. `make migrate-check` — upgrades a throwaway copy of `data/dev.db` (or an empty DB) in `/tmp/audhs-migrate/` and prints `alembic current`. Fix until clean. Only then `make migrate-apply` for the learner's dev DB (the backend also auto-migrates on start when `AUTO_MIGRATE=true`). Never test a migration on the learner's database first.
4. Update `docs/EVENT-SCHEMA.md` / `docs/ARCHITECTURE.md` data-model section if tables changed.
5. Run `backend/tests/test_export_wipe.py`, `test_db_core.py` and the full backend suite (`make test-backend`). Tests create the schema with `create_all`; the upgrade path with data is covered by `tests/test_migration_upgrade.py` (older revision → head, every table filled by reflection via `tests/_rows.py`) — extend its assertions when your migration has a data step. `migrate-check` additionally upgrades a throwaway copy of the dev DB.
6. Migration + model + docs belong in one commit (the owner runs `/commit`).

Current heads: !`cd "${CLAUDE_PROJECT_DIR}/backend" 2>/dev/null && (uv run alembic heads 2>/dev/null || echo "alembic not initialised yet") || echo "backend not initialised yet"`
