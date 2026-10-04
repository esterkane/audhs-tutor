# C6 Home topic disclosure

## Problem and change

Home already has a resume-first card and optional session settings, but the complete topic-selection form remained expanded. Collapse it behind a native “Change new-session topic” disclosure. Keep the chosen topic visible in the start/resume card and state that selection affects a new session, not the saved one. When no saved session exists, summarize the current pace, energy and questioning style near Start.

Only presentation changed. Existing preference writes, selection readiness, preparation/activation, start, review offers and resume routing remain untouched. No dependencies, new styles/tokens, fabricated review counts or learning-state changes.

## Evidence

Before editing, four existing Home resume journeys passed. After editing: nine Home resume/readiness browser journeys and twelve Home component tests pass. Browser checks cover 320/390/800/1280 widths, disclosure keyboard opening/closing, saved review resume, long select options, ready-to-empty-to-ready selection and deliberate draft activation before starting. Inspected desktop and narrow screenshots. Full frontend lint, types and production build pass; pre-existing chunk-size and spectrogram worker warnings remain. Read-only code/state and pedagogy reviews report no blockers or majors.

## Remaining C6 work

This bounded disclosure change does not complete C6. Audit current audio active-stop visibility and contextual capture/parking next; reconcile existing implementation before editing. Home still contains both new-session and resume actions in one card, and the recent-area/review composition needs a verified data contract rather than mock counts. Human comprehension and assistive-technology acceptance remain unverified.
