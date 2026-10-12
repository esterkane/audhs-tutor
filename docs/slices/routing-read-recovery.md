# Model routing read recovery

2026-10-12 — AU-MODELS-02. With503 on /api/models/routing, opening the routing
panel showed a blank area at320/1280px. A missing response is not an empty routing
configuration. The existing panel now shows loading/error/retry states, with the
shared15s boundedRead helper and no automatic query retries. Failed refresh retains
cached routing with an explicit stale-data warning.

Retry remains mounted/focusable while pending and refuses duplicate activation.
Success focuses the routing region only if Retry still owns focus. Moving elsewhere
while waiting preserves learner focus. Assignment handlers, profile selection,
benchmarking, downloads and learning/model execution remain unchanged.

Evidence: two before-fix browser failures, then six isolated browser tests pass11.5s
(routing + registry regressions). Tests cover initial503, held response, duplicate
Enter, moved/retained focus, successful read and failed cached refresh after Back.
No model POSTs occur. Existing Models unit test, ESLint, e2e TypeScript and production
build pass; existing chunk warning remains. Narrow screenshot inspected: recovery
copy/button fit; the existing routing table horizontally scrolls. No full settings
accessibility or screen-reader conformance claim. Bounded code/control review clear.

Other Models queries and physical audio/human acceptance remain separate. No backend
change or runtime inference needed. Both publication variants stay private.
