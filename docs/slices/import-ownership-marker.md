# Import recovery ownership marker

2026-10-08: Public Linux CI run37819622369 reproduced a deleted/recreated lock accepting the original device/inode. Filesystems can reuse an inode after unlink. Device/inode alone therefore cannot prove uninterrupted lock-file identity.

Implemented bounded fix: persist a random per-import marker in the private lock file and in the existing IngestRun options JSON under a version2 key. Require device/inode and exact marker bytes after acquiring the file lock. Missing/malformed/replaced marker remains unknown; never recreate recovery evidence. Old version1 imports remain unknown. No database schema, learning-state policy or automatic resume change. Assessment guards retain their existing independently checked random marker and inference seal; do not prepend an import marker to those files.

Affected files: core/local_ownership.py, knowledge/ingest/recovery.py, import ownership/recovery tests. Acceptance: deterministic reused-identity replacement test, valid hard-exit recovery, busy owner refusal, malformed/legacy evidence, unchanged assessment guard/continuation and recovery jobs. Record final evidence below after implementation.

## Verification and limits

60 ingest tests and32 targeted ownership/recovery/assessment-guard/continuation tests pass (overlapping sets), plus Ruff and strict mypy217. Two real sandbox browser journeys pass at390/1280 with keyboard explicit resume; no UI behavior changed. Independent review clear. The deterministic same-inode test mutates marker bytes in place; the original Linux deletion/recreation regression remains. Version1/malformed records stay unknown rather than being retrofitted with proof. Assessment marker bytes and inference sealing are unchanged. Live backend restarted only after checking zero running import records; health verified. Remote Linux rerun remains required; the failing prior run is not a pass.

Native browser zoom testing was interrupted and remains unverified. No application zoom/settings change was made and the temporary test tab was closed. This is separate from import recovery evidence.

CI follow-up: the same remote run also finished with5 browser failures. Two exclusion tests assumed there were no earlier superseded synthetic questions; the new publication journeys retain those fixtures. Remaining session/reading failures need trace inspection. Keep this fix uncommitted while batching the related CI repair; do not mark CI green. Logs: /tmp/audhs-backend-ci.log and /tmp/audhs-browser-ci.log. Latest legacy fixture rerun5 passed after updating its row-count expectation; it must run from backend because subprocess imports use that directory.

### Browser CI isolation follow-up
Downloaded run 37819622369 artifacts to `/tmp/audhs-ci-37819622369` and inspected failure snapshots. Two independent fixture leaks are confirmed: publication leaves its synthetic replacement selected by the later reading journey (Four/Five instead of the seeded answer), and Home delayed-preference tests leave `session.default_mode=low_capacity`, changing subsequent session plans to review/recap. Exclusion tests also see the two retained superseded originals.

Added per-test capture/restore of the prior mode in `frontend/e2e/home-late-default.spec.ts`; application learning logic is unchanged. Home plus session journeys run together: **6 passed**, including both previously failing session journeys; focused ESLint passes. Publication fixture cleanup and its ordered regression run remain next. No combined CI repair commit/push yet. Logs: `/tmp/audhs-mode-isolation.log`.

2026-10-08: Browser CI fixture isolation repaired: publication cleans only its synthetic question/source/dependencies in the sandbox, including committed lost-response replacements; delayed Home preference tests restore the prior mode. All12 ordered publication/Home/reading/exclusion/session journeys pass, focused ESLint and bounded review clear. Narrow publication screenshot inspected; keyboard and390/1280 reflow assertions retained. No application learning change. See slices/import-ownership-marker.md. Remote full CI remains to verify after push.
