# Integrated regression checkpoint — 2026-10-14

## Scope and findings

Ran the complete local frontend, backend and default Chromium suites after provisional feedback and session/recap recovery. Disposable browser sandbox only; no paid inference or live learner submissions.

- Frontend: 139 files, 717 tests passed.
- Backend initial full run: 1693 passed, four failed. Storage rollback defect and stale fixture/schema expectations fixed separately; all 22 affected tests pass. See provisional-feedback-downgrade.md. Full lint/types passed there.
- Browser initial full run: 461 passed, four failed, 20 skipped in 13.2 minutes. Skipped opt-in scenarios are not acceptance evidence.

Both Focus failures were an ambiguous `header` locator after returning Home (shell banner plus section header). It now targets the banner landmark, including hidden elements so Focus visibility assertions remain meaningful. Both secondary-heading failures expected an obsolete curriculum title. They now require the current exact “Review lesson drafts” h1. Single h1, keyboard access, font size and responsive bounds assertions remain intact. No application behavior or learning logic changed.

All four corrected browser scenarios pass in the targeted rerun (22.3 seconds). Keyboard Focus entry/exit, draft preservation, audio Stop focus, reload/Back, 200% text and 320/1280 layout checks pass. Focus screenshots at both widths were visually inspected: text wraps and retained draft/exit controls remain visible. Targeted ESLint passes; independent review confirms the banner selection preserves the intended checks. This combines the original full-run evidence with a focused rerun; it is not a second full-suite run.

## Reconciled queue

Current work and policy documents had contradictory historical status: provisional feedback described as inactive, source containment as wholly absent, and authored lifecycle/private lesson activation as unimplemented. Updated these using current code and the corresponding slice records. Fixed the workspace plan's broken rights-contract reference. This changes no policy or implementation scope.

Remaining: human explanation/re-entry comprehension, assistive technology and physical audio; independent model-grading quality validation; version-bound owner-origin/derived lineage and public-export enforcement; remaining material coverage, visual/video and authoring work. Hosted eligibility is still disabled pending origin evidence. Neither saved content nor passing automation certifies learning or factual correctness.

Latest inspected hosted CI run 38473143275 was blocked before runtime jobs by account payment/spending-limit checks. This checkpoint does not claim hosted CI passes or whole-project completion.
