# Private activation review and recovery UI

Before: course-independent answer-derived drafts rendered an unavailable message and permanently
disabled activation button. Reproduced at 1280 and 390 px in the sandbox before editing.
The learner now reviews the saved lesson, checks the exact-version confirmation and explicitly
activates it. No changes to grading, scheduling, source permissions or task qualification.

## Implementation

- Owned preview uses generated API types and existing controls/tokens. Saving/dirty/conflicting
  draft states block new activation. Preview source limitations remain readable; editing and
  discarding are preserved. Existing shared activation remains separate.
- A bounded learner/draft-specific browser record retains the exact command and idempotency key
  before sending. Storage failure prevents submission. Reload never submits automatically.
  Explicit retry preserves the request; corrupted recovery requires explicit replacement after
  checking status. Leaving a page prevents stale callbacks from updating it.
- A receipt reports actual created counts, never preview defaults. Source-check/identity and
  activation consent are explicitly separate from factual verification and assessment review.
  An authoritative recovered receipt supersedes an earlier lost-response error.
- Legacy unavailable copy is removed from the private draft display without editing its stored
  source/history record. Other warnings remain. Home is the next navigation action after success.

## Verification

Full frontend suite: 678 passed before three final recovery regressions; all 21 final focused component/route tests pass. Lint/types and production build pass (existing bundle-size warning). Backend code did
not change; reuse the 1630 passing backend tests from the preceding API slice.
Two sandbox browser journeys pass at 1280/390 px: keyboard confirmation, simulated connection
loss, reload without a POST, explicit same-key retry, receipt on subsequent reload, no shared
publication calls, axe main-region checks and no horizontal overflow. Dark theme with 200% text
at 390 px and 200% CSS zoom at 1280 px also checked; reduced motion configured.
Screenshots inspected before/after, including /tmp/audhs-private-activation-review-390.png,
/tmp/audhs-private-activation-after-1280.png and dark/zoom variants.
Browser transport is mocked synthetic data; backend atomicity is established by API/repository
regressions, not these UI mocks. No real saved lesson activated during validation.
Code and pedagogy reviews found no blocker/major; the final error-display delta also passed review.
Final sanitized focused tests and type checks pass; publication guard passes. Snapshot unchanged.

## Remaining

Human comprehension acceptance remains open. Native browser zoom was not separately tested;
the CSS zoom and enlarged-text checks provide reflow evidence only. Existing course picker/top-of-page density remains
outside this bounded change. This slice enables learner-controlled private activation, not batch
activation or automatic approval of other drafts. Broader project/UX queues remain open.
