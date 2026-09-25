---
name: audhs-state-reliability
description: Design and verify AuDHS Tutor submission retries, checkpoints, draft recovery and asynchronous UI state. Use when lost work, duplicate evidence or stale requests are possible.
---

# audhs-state-reliability

SQLite/kernel owns learning progress, competency and FSRS. Browser stores may recover temporary work but cannot award mastery or independently advance the session. Read the relevant R1–R4 gates in docs/AUDIT-IMPLEMENTATION-PLAN.md and existing data/event rules.

For a mutation, specify intent identity, payload fingerprint, learner scope, atomic write set, transaction owner and retry semantics. Equal key/equal payload returns the original result; equal key/different payload conflicts. Handle concurrent duplicates with database constraints, not only disabled buttons. Keep model/network work outside long transactions; record billing/model-call outcomes independently so rollback does not erase real usage. Do not claim exactly-once model execution solely from idempotent learning writes.

For asynchronous UI, guard all callbacks and finalization by request identity. Abort is not sufficient. Preserve delivered partial text, prompts and unsent answers. Distinguish stopped, failed, partial and complete. Only OPEN WebSockets accept sends; worker error/dispose/timeout must settle outstanding work with one cleanup path.

For queues and drafts, use stable IDs and content versions, never positions in a mutable query list. Define conflict, expiry, purge and storage-failure behavior. Keep pending UI distinct from server-confirmed progress. No modal or confidence answer may block simply stopping.

Test lost response after commit, failure between writes, two concurrent requests, old stream completion after a new request, refetch/remount, storage denial and content-version conflict as relevant. Assert persisted row/evidence counts and actual checkpoint identity, not just UI copy. Use disposable data and check migration/export compatibility.
