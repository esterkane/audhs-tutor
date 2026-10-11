# Notebook setup command recovery

Status: architectural boundary identified; implementation next. This is not an accepted retry-policy change.

## Current evidence
`NotebookLab.start` schedules an asyncio task and returns immediately. It ignores another start while that task is active but retains no request identity or immutable payload receipt. `/api/notebooks/status` returns only the latest course/status/message/URL. The service is recreated on backend startup. The frontend start mutation has no deadline; a lost response can leave cached idle state and an error while the job continues. The existing bounded status GET is intentionally not a solution to this command ambiguity.

## Smallest coherent vertical slice
1. Give each explicit setup command a client request ID and bind it to course ID plus install boolean. Repeated equal identity/payload must return that command's state without reinstalling; changed payload conflicts. A different command while setup runs reports busy without claiming it was accepted.
2. Return a service-instance identity and command identity with status. Keep a bounded per-instance receipt store separate from the latest global status; do not confuse another course's job with this command. Backend restart means unknown old outcome, not permission to retry. Durable job recovery across process death remains a separate phase.
3. Retain the pending ID and payload in tab-local storage before sending, never the token-authenticated URL. If storage fails, disclose in-memory-only recovery. A bounded POST timeout means acknowledgement unknown, not job cancelled. Do not automatically resend.
4. Offer explicit Check setup status with a read-only command lookup. Matching accepted/running/terminal states recover the UI; absent/restarted-instance outcomes preserve uncertainty and original request. A new setup action must not be silently substituted for recovery. Exits and notebook links remain usable when available.
5. Scope late callbacks by request and course identity. Cancel obsolete reads before applying accepted start state. Keep old working files untouched and install consent tied to the original payload.

## Files and invariants
Likely changes: backend notebooks/lab.py and api/notebooks.py, LocalNotebookLab and its tests, generated API types, and notebook browser journeys. No learning kernel, grading, FSRS, notebook-cell execution, model routing or package changes. No authentication tokens in local storage, receipts persisted to disk, logs or public fixtures.

## Verification gates
Backend: duplicate and conflicting commands, busy other course, response lost after acceptance, bounded receipt eviction, backend-instance replacement, no duplicate installer, preserved learner files and shutdown. Frontend: timeout, storage denial, remount, course switch, stale response, double click and explicit lookup; never a second POST from recovery. Browser: lost acknowledgement and eventual completion, desktop/narrow keyboard paths and status visibility. Preserve current notebook tests and local-only API checks; obtain bounded review before publication.

## Remaining decisions
A durable restartable installer is larger than this in-memory service. Do not add SQLite job tables or automatic installation resumption without a separate ownership/child-process recovery design. This phase should clearly retain unknown outcomes across restart rather than pretending that the old operation never happened.

## Backend implementation in progress
Service-instance and request identities now support equal-payload replay and read-only command lookup. Different payloads conflict; busy setup rejects another command; backend-instance mismatch/unknown IDs stay unknown. A128-entry per-instance store refuses new commands when full instead of evicting IDs and accidentally allowing replay. Legacy start remains compatible. No disk receipt store or automatic restart was introduced.

13 notebook backend tests pass, including existing file-preservation/shutdown tests and new lost-acknowledgement, completed-receipt, changed-install-consent, busy-other-course, full-history, restarted-instance and API/no-store checks. Ruff and full backend mypy217 pass. Logs: /tmp/audhs-notebook-commands.log and /tmp/audhs-notebook-command-mypy.log.

Not committed/pushed or activated locally yet: frontend pending-record storage, bounded command acknowledgement, command lookup UI, stale-response guards, generated schema, browser acceptance and review remain to finish this vertical slice. The current UI still uses the legacy start path. Avoid claiming end-user recovery is delivered from backend tests alone.

## 2026-10-11 continuation — review regression coverage
Frontend command recovery is now implemented locally (the earlier frontend-next paragraph is historical). Added regressions for terminal receipt storage-cleanup failure with explicit memory-only recovery, and historical course results while another course is installing. The latter verifies the active job stays visible, setup stays disabled and live polling continues. All 11 focused hook/component tests pass; focused ESLint and TypeScript check pass after fixing an unused test argument. No learning logic changed.

Still uncommitted and not activated: final browser rerun/visual verification and review remain. The preceding browser run recorded three passes and two lost-response recovery failures before the receipt/live-status separation; do not treat it as acceptance of the current implementation. Publication is deferred until these gates pass.

Follow-up review found and fixed the same cleanup failure on explicitly rejected busy/full commands. The hook now retains exact rejected-request evidence; explicit memory-only recovery releases only that proven-unaccepted request, without resending. New regression passes. Final focused frontend count12; backend14, Ruff, mypy217, focused ESLint and production build pass. Bounded re-review reports no remaining blockers/majors. Browser recovery fixture corrected to respect the URL-restored notebook view after reload; final five-journey rerun is pending. Earlier runs interrupted during source edits are not acceptance evidence.

Final browser acceptance: all5 notebook journeys pass (40.4s), including390/1280px lost acknowledgement→reload→keyboard GET-only recovery, single POST, no token storage and no horizontal overflow. Narrow and desktop recovery screenshots inspected. Final log: /tmp/audhs-notebook-command-browser-final.log. Ready for paired publication; not yet committed, pushed or activated.
