# C6 Home recent areas and review visibility

## Evidence and implementation

Home had no recent-area return links even though tab-local browse history already exists. Reuse that store and the shared area catalog to show up to three valid recent destinations. Label them “Recently browsed areas,” not learning progress or paused sessions. Missing/deleted areas and load/storage failures are disclosed; browsing remains separate from learning goals. Existing tokens/Card primitives are reused.

The existing current-session response computes due_reviews with a cap of100, excluding language and honoring the checkpoint skill scope. Display its count on the saved-session card, using “At least100” at the cap and no fabricated count when no verified session/count exists. Do not call /review/due for Home decoration: inspection found that capped queries can emit adaptation events. No new API, learning writes or planner shortcut is introduced. Quick review without a session requires a separate entry contract; the existing plan's review choices remain intact.

## Verification

Baseline recent-link journey failed because no such entry existed. Final Home browser suite:12 journeys passed, including saved resume, ready/empty/preparation flows, recent-area keyboard navigation/Back/reload, absent deleted links, lookup failure/retry, no review endpoint calls or learning mutations, and320px/200% text with long titles.14 Home/browse-store component tests passed. Full frontend lint, types and build passed; inherited bundle/worker warnings remain. Desktop and390px screenshots inspected. Read-only state and pedagogy reviews cleared the slice; wording simplified from “scope” to “for this saved session.” Sanitized checkout reruns the three new journeys.

## Outstanding scope

Recent browsing is not recent learning: no per-area completion, timestamps, multiple paused sessions or recreated notebook/media state is implied. Home's existing Resume and Start actions still share a card; reconcile their separate intent and verified current-session behavior before declaring C6 complete. A short Continue button with target/phase outside it remains part of the authoritative ResumeCard composition. C7 typed recent contexts/global search remains unfinished, as do backend capture undo/idempotency/source returns. Human comprehension and assistive-technology acceptance remain open.
