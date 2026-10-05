# Preferences read recovery — Stage2a

2026-10-04. Two baseline browser cases reproduced a503 read leaving Preferences on Loading with no recovery. The correction is limited to Preferences and its existing shared read/save hook; backend preference values, learning logic and model routing are unchanged.

## Behavior

An initial failure now shows a plain-language error, Retry loading preferences and Return Home. Technical detail is optional. A failed refresh preserves cached settings with explicit stale-data wording. Retry does not write settings. The shared preferences read now uses the existing15-second bounded-read helper and no automatic retry; explicit cancellation prevents ignored/late transport results from being accepted. This deadline applies to all existing consumers of that shared query, not just the page.

Before a preference save, cancel an in-flight preference read so its earlier snapshot cannot overwrite the successful save response. This does not solve every concurrent-save ordering problem, serialize all settings changes or claim a failed save definitely did not commit. Existing mutation error handling remains.

## Verification

Five browser checks passed: initial failure, keyboard Retry, successful load, failed refresh with retained controls, exact outgoing preference save and no horizontal overflow at390/1280px; existing heading/loading/Back checks remain passing. Sixteen existing Home/adaptation/bounded-session-read unit tests passed plus two new hook tests: hung read settles after the deadline without retry loop, and ignored-abort late read cannot replace a successful save. ESLint, types and production build pass; known large-bundle/spectrogram-worker warnings remain. A first test-file write used the wrong directory and was corrected before the two new tests ran; no missing test is counted as passed.

Screenshots inspected: [initial narrow failure](../ux/evidence/preferences-recovery/failed-read-390.png) and [cached desktop failure](../ux/evidence/preferences-recovery/cached-read-1280.png). Fixture replies isolate read/save outcomes; this does not verify all backend outages, actual user comprehension or screen-reader behavior. No live learner data was used in browser tests.

## Remaining

Map, Vocabulary, Experiments and Models still need their own failed-read corrections. Preferences units/grouping, failed-save ambiguity and concurrent-save ordering are separate work. A successful empty preference registry remains the existing empty controls state, not invented defaults. Next bounded slice: Map read recovery, preserving map contents and learning selection.

Independent read-only code review found no blockers or major findings; reviewer did not execute tests.


Follow-up2026-10-05: same-client preference writes now share a serial mutation scope to prevent reversed full-snapshot responses. Five hook/four browser tests, lint/types/build and review pass. See docs/ux/DAILY-LEARNING-ACCEPTANCE.md for evidence and remaining cross-tab/transport/read-order limits.
