# Slice: db-core (Stage 0)

**Story.** As the owner I want every Phase-1 table to exist with `learner_id`, ULIDs and UTC timestamps so later slices only add rows, never structure.
**In/out.** ORM in `backend/app/db/models.py` (32 tables, ARCHITECTURE §4); Alembic migration `08e0e269a737`; async engine/session on `app.state` (no singletons); WAL + foreign keys via pragmas.
**Guarantees.** `learning_event` is append-only by SQLite triggers (`app/db/ddl.py`), created by both `create_all` and the migration; `scripts/export.py` / `scripts/wipe.py` are the only sanctioned delete path (wipe drops + recreates the guards in one transaction).
**Events.** None emitted here; the envelope columns are the table.
**Mode/energy.** n/a. **Accessibility.** n/a (no UI).
**Verified by.** `tests/test_db_core.py` (table set, learner_id coverage, WAL/FK, append-only, migration == metadata), `tests/test_export_wipe.py`.
