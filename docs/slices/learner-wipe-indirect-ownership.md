# Learner wipe — indirect ownership and rollback

Repair two FK failures discovered by authored-visual recovery tests: cached
representations reference owned model calls, and experiment arms reference owned
experiments without carrying learner_id themselves. Export includes those attributable
rows; explicit wipe removes them before their parent. Shared corpus and unattributable
representations remain. Other learners' records remain unchanged.

The transaction now begins before dropping event guards, so failures restore guards
as well as rows. No UI, grading, scheduling, inference or migration changes; no actual
learner wipe is performed by this implementation work. Existing explicit wipe is the
only destructive entry point. Browser/keyboard/responsive behaviour is unchanged.

Regression fixtures populate every table for two learners and add a shared cache
entry. An injected mid-wipe failure checks complete rollback and guard restoration.
17 focused wipe/export/visual-storage tests pass. Both initial regressions failed
before the fix (missing indirect export rows; lost event guards after rollback).
Bounded review found no blockers/majors. Full-suite/lint outcome recorded below.
Follow with the authored-visual transactional service. This is a code repair, not
execution of a wipe against the learner database.

Final verification: **1479 backend tests passed** (3 existing dependency warnings);
`make lint` passed (Ruff/format, mypy254, frontend TypeScript/ESLint). Private snapshot
verified unchanged. No migration or live wipe performed.
