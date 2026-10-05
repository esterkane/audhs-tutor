# Import restart recovery — bounded implementation plan

Status: new owned-run crash recovery implemented and verified; legacy ownership and durable job-ID recovery remain open. R10/T04 follow-up, 2026-10-05.

## Observed failure

A disposable SQLite test ran ingest_path in a child process over two synthetic Markdown files with media and retrieval indexing disabled. The child exited with os._exit(77) after the first committed file. The API then returned a durable run with status running and files_done=1; trying to resume returned409, only interrupted runs resume. Test passed as a characterization of the failure. Probe retained outside the repository at /tmp/test_ingest_crash_probe.py; output /tmp/ingest-crash-probe.log. No live database, course source or model was used.

The in-memory jobs map cannot prove ownership after a restart. The service records runs for API and CLI callers alike. Job IDs and durable run IDs differ, and no durable linkage currently survives loss of the map. Corpus only offers interrupted records for resumption. Graceful cancellation already marks interrupted; do not rewrite that working path.

## Required outcome

After a worker crash, show the last saved file count and an honest interrupted state, preserve committed documents/items and original options, and offer an explicit resume. Never claim an active CLI or other backend worker is interrupted. Never resume automatically or treat a timeout as proof of termination. Do not change curriculum, assessment, scheduling or model routing.

## Architecture decision (implemented in ADR-0018)

Use local OS ownership rather than elapsed time as proof that a worker is gone. Proposed same-host design: a per-run advisory lock, acquired before publishing a running record and held for the entire run by every API/CLI entry through ingest_path. Reconciliation must acquire that same lock exclusively before changing a running record to interrupted, then re-read status inside its transaction. Lock availability, not PID existence or a heartbeat expiry, is the proof. Crashes release OS locks. Never unlink lock files while contenders can hold their inode. Database identity must namespace lock paths consistently across API and CLI; handle canonical paths, file permissions and in-memory test databases explicitly. A lock cannot prove anything across different hosts or unsuitable network filesystems; do not silently support those cases.

Alternative: a lease/heartbeat protocol. It adds expiry and fencing complexity and cannot by itself distinguish slow workers from dead ones. A blanket startup UPDATE and PID-only checks are rejected. Confirm the local lock contract against existing supported platforms and document the decision; do not introduce a queue service or new package by default.

## Implementation sequence and likely files

1. Define and test the ownership primitive in knowledge/ingest, with disposable subprocess cases (live holder, hard exit, two reconcilers). Acquire before durable run creation; release only after terminal state handling. Legacy running rows lacking ownership evidence remain explicitly unknown; no automatic reclassification.
2. Integrate through service.py so API and CLI share the contract. Add durable job-to-run linkage with backward-compatible storage/migration as needed; jobs.py must persist identity before acknowledging a job. Include failures before ingest_path creates a run. Do not reconstruct a complete detailed report from incomplete counts.
3. Add reconciliation at an explicit service boundary and durable read fallback in api/corpus.py. Missing transient state must resolve to persisted status when identity is known. Guard concurrent resume claims; two resumes must not create parallel continuations or mark the predecessor resumed without a viable continuation. Preserve original path/settings and trust restrictions.
4. Update Corpus and its query hooks to distinguish running, interrupted, terminal and unknown legacy ownership, with saved counts, read retry and explicit Resume. Failed reads must remain uncertain. Restore links across reload; no automatic re-import or silent fallback to current form settings.

## Acceptance and stopping criteria

- Hard exit after a committed file: restart reconciles only the abandoned owned run; completed versions/items unchanged; explicit resume imports only remaining/retryable work using original options.
- A separate live CLI/backend owner is never interrupted by reconciliation, regardless of age.
- Crash before run publication, between run creation and progress, during index/SQLite boundary, and after terminal commit: honest outcomes; no invented exactly-once model execution.
- Concurrent reconcilers/resumes cannot duplicate a continuation; locks and transactions have one documented owner.
- Legacy rows and unsupported ownership environments stay unknown with clear recovery limits.
- Keyboard/narrow browser journey demonstrates restart recovery and no automatic POST; API/unit/migration tests assert persisted identities and counts.
- Code/reliability review before publication. Public fixture data must remain synthetic; private material stays private.

This is a larger ownership change, not a UI-only fix. Ship a coherent recovery slice only after the proof-of-ownership and durable identity tests pass. Until then the existing safe limitation remains: graceful stops resume, hard exits require a reviewed new normal import using content deduplication. Broader drafting/model-job recovery is separate.

## Ownership foundation evidence — 2026-10-05

`knowledge/ingest/ownership.py` now provides nonblocking same-host POSIX ownership. New identities create private lock files exclusively; recovery must supply the original device/inode identity and cannot create a missing file. Canonical database symlink aliases share storage. Busy locks return busy; missing, replaced, unsafe-permission, symlinked and hardlinked evidence raises unknown ownership. The application never unlinks lock files. Normal context exit releases descriptors; a hard child-process exit releases the OS lock. No third-party dependency or runtime integration was added.

Six isolated tests pass, including a live child and os._exit(77), missing/replaced evidence, duplicate acquisition, path validation and private permissions. Targeted ruff/format and strict mypy pass. Bounded independent review found no blockers; its integration condition is to persist identity before the running record and hold the lock through final durable state. This is NOT a claim that restart recovery works in the app.

This foundation was subsequently connected and verified in the integration below. Legacy unknown ownership and durable transient-job identity remain open.

## Connected recovery evidence — 2026-10-05

The import service now creates ownership before a new durable run and holds it through terminal commits. Backend startup and CLI import/list entry reconcile abandoned owned records using dedicated sessions and a status/options compare-and-set. Interrupted continuation claiming is atomic with new-run creation. CLI retrieval initialization now follows saved index-option restoration; no-index recovery does not require an embedding model. No schema migration or learning state changes.

Verification: full backend suite896 passed before the final CLI/startup test additions; final five recovery tests pass, alongside six ownership and eight existing progress tests. Ruff/format and strict mypy pass (202 source files). A live child with an intentionally old start time is not interrupted; after os._exit(77), concurrent reconcilers recover exactly once. HTTP resume preserves the original document version, imports only the remaining file, and retains trust/media/index options. Concurrent resumptions create one continuation. App lifespan and CLI saved-index behavior are explicitly exercised.

Two real Chromium sandbox journeys at390/1280 create a hard-exited synthetic import, invoke the startup reconciliation function, open the missing transient-job URL and resume through the existing interrupted list using the keyboard. No import POST occurs before the explicit action; one POST completes remaining work, with no horizontal overflow. Narrow result screenshot inspected. Browser tests do not restart the browser-managed server; actual lifespan wiring is covered separately in the backend test. Bounded independent code/reliability review found no blockers. No live learner data or model was used.

Remaining: legacy records without trustworthy lock evidence stay unknown; the in-memory job URL still returns404 after restart and directs the user to interrupted runs. Failure before durable run creation, persistent queued-job identity, full historical report reconstruction, other job types, network filesystems and hard-linked database aliases are not covered. No automatic resume. Earlier planning paragraphs describe the full target; this delivered slice does not close R10.
