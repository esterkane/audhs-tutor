# Map read recovery — 2026-10-04

## Problem and change

Reproduced a 503 response at390/1280px: Map remained “Loading map…” with no recovery. The query now uses the existing15-second boundedRead helper with no automatic retry. Initial failure provides Retry and Home; failed refresh retains and labels the cached map. Both loading/error and ready states have a contextual h1. Diagram, nodes, prerequisite locks, mastery and Learn this navigation are unchanged. No backend, model or learning-state policy changes.

Files: frontend/src/features/map/api.ts, routes/Map.tsx and focused hook/browser tests.

## Evidence

Before change:2 browser failures with the false-loading state. After change:2 browser journeys pass (8.2s), including keyboard retry, Home/Back, retained diagram/nodes, disabled locked node, keyboard lesson navigation and no horizontal overflow at390/1280. The test must wait for Home to render before Back; URL alone can precede React route completion. Final screenshots wait for the SVG and were visually inspected.

Two unit tests pass: hung read deadline/no auto retry, existing mastery/memory/locks/selection contract. Whole frontend lint, TypeScript and production build pass; existing large-chunk and spectrogram worker_threads warnings remain. Independent read-only code/recovery review found no blockers or major findings; reviewer did not run tests.

Screenshots: ../ux/evidence/map-recovery/ (failed-read and cached-read at both widths).

## Remaining and next

The existing floating Park button overlaps the locked row in the390px screenshot; this belongs to the queued shell/overlay correction and is not declared fixed. Diagram renderer errors and empty-map guidance remain separate. Real screen-reader/human comprehension and broader responsive/zoom acceptance are unverified. Other failed-read routes remain open.

The new owner-provided navigation proposal is reconciled in ../ux/CONTEXT-WORKSPACE-PLAN.md before further page redesign.

Sanitized checkout independently passed the same two unit and two browser checks. Publication guard passed.
