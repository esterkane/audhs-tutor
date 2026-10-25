# Confirmed block transitions and stale reads

## Scope — 2026-10-25

The preceding notebook release's CI finished with 495 passing browser journeys and one failure
in code-practice setup: the expected Learn screen did not appear after continuing the plan.
Other gates passed. Investigation reproduced a session-cache race independently of timing:
an earlier session read can replace a server-confirmed next block. The original CI log alone
does not prove that every possible failure at that heading has this cause.

Block start/next/end/extend now cancel reads for the exact session and current-session cache
before writing and again before publishing the confirmed response. Cancellation does not
revert a newer cached value. Both caches receive the confirmed block only for the matching
session identity, then current-session data is refreshed. No client chooses the next block,
checkpoint or learning evidence. Existing server idempotency and per-hook single-flight rules
remain authoritative; mutation failures are not retried automatically.

Two controlled regression cases (reads started before/during the write) fail with the prior
implementation and pass with this change. They deliberately allow the old transport to resolve
late and require the confirmed phase to remain in both caches. Full frontend: 799 tests pass;
ESLint, TypeScript and production build pass. All 23 affected browser journeys pass, including
the failing code-practice path at both widths, lesson reading/feedback/recap, checkpoints,
late-navigation ownership, pause/resume and the new checked-calculation authoring flow.
Ten additional repeated code-practice journeys at both widths also pass.

This is a frontend-only follow-up to the checked-calculation release. Reuse its backend
regression evidence for unchanged code; do not claim general tutor factual accuracy or faster
decoding from this cache fix. Main data/history, routes and authoring budget are unchanged.
New exact-release CI remains a separate snapshot gate.
