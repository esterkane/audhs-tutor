# C6 capture transaction boundary

Inspection found that session and standalone thought creation committed before emitting PARKED. Promotion also committed status before emitting PROMOTED. EventWriter already commits the event and any pending changes together. Use flush to assign the item ID, then its existing event commit to persist both. Request cleanup rolls back a failed transaction.

Scope: backend/app/api/parking.py, backend/app/orchestrator/tools.py and failure-injection API tests. Preserve endpoint schemas, event semantics and learning logic; no new library, migration or UI behaviour. This is a prerequisite for reliable capture recovery, not retry deduplication. An ambiguous network response after a successful commit still requires durable intent IDs, separately documented in capture-recovery-contract.md.

Verification: 22 backend tests passed in original and sanitized checkouts, including standalone/session creation audit failures, successful retry with one event, and promotion rollback. 11 isolated browser capture/action journeys passed (narrow/desktop, keyboard/focus, draft refresh, failures and timeout). Targeted Ruff and mypy passed; test formatted with Ruff. Read-only transaction review found no blockers or majors. No visual markup or learning-state decision changed. Network ambiguity after commit and durable source-return remain open.
