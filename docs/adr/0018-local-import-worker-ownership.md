# 0018 — Local import worker ownership and crash recovery

Date: 2026-10-05
Status: Implemented for new same-host file-backed SQLite imports

## Context

A hard worker exit preserves committed import items but leaves a running record that cannot resume. API and CLI imports share SQLite, so absence from one process's job map or an old timestamp does not prove the worker is dead. The requested recovery must preserve completed content and original settings without interrupting another worker.

## Decision

Use standard-library POSIX advisory locks for the supported local-filesystem deployment. Each new recorded import creates an exclusive private lock file before committing its running row, persists its device/inode identity in the versioned options marker `_local_owner_v1`, and holds the descriptor through terminal commits. Canonical database symlink aliases share the namespace; hard-link database aliases and network filesystems are outside the contract. Lock files are never deleted by the application.

Backend startup and CLI import/list entry reconcile using separate short database sessions. Recovery must acquire the existing lock nonblockingly with the persisted identity, then conditionally change a matching running row to interrupted. A live owner, legacy record, unsupported environment, missing or replaced file, unsafe permissions or malformed identity never proves abandonment. No age-based expiry and no automatic resume. Interrupted continuation claim and creation commit together; a second claimant cannot create another continuation.

The existing interrupted-runs interface is the explicit recovery entry. Original options remain authoritative; CLI now resolves indexing after loading those saved options. The local mechanism does not guarantee exactly-once inference, reconstruct lost job reports, repair a derived retrieval index or award learning evidence.

## Consequences and limits

No new dependency, queue service, schema migration or hosted call. Restores without lock evidence remain unknown. Small lock files accumulate and must not be unlinked while users of the namespace may exist; cleanup requires a future proven quiescence protocol. Old abandoned runs cannot safely be adopted automatically. Transient job-ID persistence, failures before a run exists, broader draft/model jobs and full report recovery remain separate work. Unsupported ownership does not block ordinary ingestion; it retains the previous unknown-after-crash behavior.

Evidence: ownership tests, real subprocess crash/resume with version identity checks, concurrent reconciliation/continuation tests, application lifespan reconciliation, CLI saved-index test, and desktop/narrow keyboard browser recovery. See docs/slices/ingest-restart-recovery-plan.md.
