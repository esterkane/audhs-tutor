# Stale plan recovery — 2026-10-15

Owner approved reviewing an updated plan rather than replacing a running activity from an old snapshot.

## Delivered

Plan proposals and Undo bind to the exact session plan, version, energy and activity boundary. Stale actions return a conflict without writing. Explicit refresh creates a persisted preview; separate acceptance is required. Completed/current activities and the current timer remain intact. Superseded proposals remain historical without fabricated learner choices. Negative suggestion preferences are preserved. Stale Undo adjusts future activities using earlier settings; subsequent preview refresh preserves this intent. It does not restore removed activities or rewrite the current energy self-report.

UI previews list future activities/durations, focus the preview heading, distinguish failed review/apply, and prevent applying a known stale or already applied preview. No model call, dependency, migration, grading, mastery or FSRS change.

## Verification

- Original two stale-snapshot regressions failed before implementation.
- 59 affected backend tests pass, including 15 snapshot/recovery cases; failure after preview creation rolls back the complete database mutation.
- Six adaptation component tests pass: separate review/apply, bound session identity, focus, decline errors, second progression conflict and existing preference choices.
- Four real-backend Chromium journeys pass: proposal and stale Undo at 1280/390px; keyboard activation, persisted preview without plan mutation, protected prefix and running timer checks, no horizontal overflow. Dedicated disposable database and ports, no paid models.
- Desktop and narrow proposal screenshots visually inspected. Production build and lint/type checks pass. Existing bundle-size warnings remain.
- Code review found loss of earlier-energy intent on a second Undo-preview refresh; fixed, regression added, reviewer confirmed. Pedagogy review found no blocker/major.

## Limits / next work

This is bounded recovery coverage, not complete lifecycle acceptance. Broader concurrent progression/refresh permutations, legacy-data browser recovery, VoiceOver and human re-entry remain to be exercised. Reload/return is now covered below. Internal tutor checkpoint writers and unrelated preference transactions remain outside this slice. Continue integrated daily-learning acceptance; do not claim the complete UX queue finished.


## Recovery acceptance follow-up — 2026-10-15

17 focused backend cases now pass, adding unbound legacy proposal rejection with whole-database no-write comparison, explicit refresh/acceptance, and two independent concurrent refresh workers returning one preview with no decision rows. Four real-backend browser journeys now reload/return Home before acceptance; persisted plan/checkpoint remain unchanged and exactly one Apply action is offered. Both proposal and stale Undo previews retain the separate keyboard acceptance step at 1280/390px. Targeted lint, format and frontend types pass. Code review clear. No production or learning-logic change.

GitHub run 38707917662 (sanitized 08c9fc4) failed before runtime jobs started. Its check annotation explicitly reports recent payment failure or a spending limit requiring adjustment. Local checks do not establish hosted CI success; no rerun or billing changes performed.
