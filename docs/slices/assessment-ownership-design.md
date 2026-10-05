# Assessment ownership: implementation design

Date: 2026-10-05. Status: design prepared for the next R3 slice; no new recovery enabled.

This extends the local ownership approach of ADR-0018 without changing its import namespace or claiming that filesystem locks recover lost model results.

## Storage and compatibility
- Add nullable `assessment_execution.owner_json`; do not change existing phase meanings or execution schema_version1. Null means unknown ownership, including all migrated legacy rows.
- Version the metadata independently: version1, fixed assessment namespace, device and inode identity. Store no full filesystem path, process command, credentials or learner content.
- Keep ownership evidence separate from request_json so payload fingerprints and completed replay identity remain unchanged.
- Restores must invalidate execution ownership even when the original lock file survives. A restored prepared row may predate inference that already occurred. Merely reacquiring its original device/inode is insufficient. Lock files are not archive members; never recreate missing evidence during classification.
- Verify old-schema upgrade/downgrade and both backup scopes with nonempty legacy and owned executions before applying any migration to the live installation.

## Shared primitive and lifecycle
Extract the existing nonblocking standard-library POSIX primitive to a shared local-ownership module only when adding its assessment caller. Keep RunOwnership's existing import namespace and call contract through an adapter. Use a distinct fixed assessment namespace; arbitrary user-controlled namespace/path input is forbidden. Existing import ownership/recovery tests must still pass.

A new assessment claim can acquire ownership before committing its prepared execution. Hold the descriptor through inference, grade persistence and learning completion, closing in finally. A crash before ownership is recorded remains unknown. Unsupported local ownership must not make normal grading unavailable; it retains conservative unresolved recovery.

Classification is read-only: acquire the exact existing lock, then re-read generation, owner metadata, phase and response. A held lock, missing/replaced/insecure file, unsupported database, unknown version or inference_started phase never permits pre-inference recovery. Do not use elapsed time or process IDs as proof.

## Restore rollback gate — required before implementation
A snapshot can capture prepared work, the original then runs inference/completes, and restoring that snapshot rewinds the database while the original unlocked file survives. Ownership proves liveness, not that inference never happened after the snapshot. Independent architecture review identified this as a major gap in the initial proposal.

Audit every supported restoration path, including local snapshot tooling. Restore must clear/invalidate recovery ownership regardless of whether files survive. Out-of-band database rollback must not be declared safe merely because a lock matches. If it cannot be reliably identified, add a non-restored, durable execution-generation/boundary mechanism before enabling prepared continuation; otherwise keep classification unknown. Do not ship a lock-only recovery classifier while this is unresolved.

Mandatory test: snapshot prepared → inference/complete → restore snapshot with original lock retained → classification remains unknown and retry never calls the model. Also cover restored stale content tokens and owner metadata copied to a different installation. This gate is additional to missing-file/lock-replacement checks.

## Explicit continuation contract
An eligible prepared request may offer an explicit resume action using its existing identity and original answer, while holding ownership. Revalidate private content fingerprint, owned active session and request consistency; reject changed/deleted questions and ended sessions. Reconcile process-rotated public content tokens internally only after fingerprint validation. Do not force the client to invent a new submission identity.

Prepared continuation must skip duplicate prepare creation only after that verified claim/phase check. The ordinary submit path must continue returning409 for unresolved identities. Two continuation calls serialize through ownership and the claim transaction; neither may replay inference once phase becomes inference_started. Grade-ready and completed requests retain existing no-inference recovery. No automatic grading on startup.

## Evidence and limits
Inspected ownership.py, import reconciliation, assessment request/execution transitions, model fields and backup/restore allowlists.21 existing backup/assessment-execution/import-ownership tests pass (/tmp/assessment-ownership-compatibility.log). Earlier real process-exit tests separately prove retained staging and blocked retries. These tests validate current contracts, not the proposed new field or continuation endpoint.

The implementation gate remains the matrix in assessment-prepared-recovery-plan.md. A migration, exact-request API, learner UI and live-worker/dead-worker/concurrent/restore tests are still required. No queue dependency, hosted provider, blanket cancellation reclaim or remote exactly-once guarantee is proposed.
