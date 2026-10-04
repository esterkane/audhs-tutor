# C1 grouped navigation — 2026-10-04

## Problem and implementation

The existing shell mixed learner activities, standalone tools and management destinations. Replaced the single More tools bucket with Learn, Explore, Library, Tools and Manage disclosures; Home and Projects stay direct links. Existing path contracts remain. All15 destination links are asserted, including source/draft/model/experiment controls, vocabulary and standalone labs. Learn offers Start or resume through Home's existing authoritative session flow rather than trusting a remembered client ID. Current nested destination is named in the collapsed group. Existing titles, main focus, content widths, audio owner and Companion lifecycle remain.

Only application file changed: frontend/src/app/App.tsx. Existing tokens/native details/links; no libraries, backend, source data, mastery, assessment or session policy changes. Updated affected navigation tests.

## Verification

Four shell unit tests passed.25 distinct targeted browser journeys passed: shell orientation3, preferences heading3, preferences recovery2, audio controls2, session pause9, Home resume4, saved answers2. Final shell rerun3 additionally checks Back/Forward and captures both ordinary and200% text views. Existing session tests compare actual disposable checkpoints and check no writes from Pause; saved-answer tests exclude generation/session POSTs. All tests use isolated services and model-free fixtures, not live learning data.

Whole frontend ESLint, TypeScript and production build passed after correcting an initial tuple-union typing error and unsupported unit-test locator option. Existing large-chunk/spectrogram worker_threads warnings remain. No whole-app or cross-browser conformance claim. Independent read-only review found no blockers/major findings; reviewer did not execute tests.

Visual evidence in ../ux/evidence/grouped-navigation: desktop ordinary view and320px200% view inspected; browser checks also cover390px. Header axe checks pass, keyboard skip/disclosure/route focus and exact current destination pass; no horizontal overflow at tested sizes. One additional disclosure step now opens formerly primary tools; management no longer competes in the same miscellaneous list. This is a tradeoff to validate with the owner, not measured cognitive improvement.

## Remaining and next

Park's existing fixed overlay still covers part of expanded navigation at320px200% text; this is not accessibility-complete. Native disclosures expand the header vertically; mobile sheet/sidebar shell layout and persistent tutor remain later work. Existing route-local unsaved state limitations from C0 remain. No area selector or recent-context recovery yet. Next bounded work should remove the reproduced Park obstruction before area context, preserving capture and focus behavior. Then C2 separates browse area from current learning target.
