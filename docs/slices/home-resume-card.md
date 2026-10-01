# Home: resume before setup

Q1 bounded slice, UX26-F2/F7: put a named saved-session card and its real next action before setup. Existing routes, selected-lesson flow, session lifecycle and topic preferences remain authoritative. Session mode/energy/style remain available under optional Session options. No new API, model call, learning event, schema or dependency.

Reproduction: Home placed topic/setup/reminders above Resume. A stale local session ID could show Resume even when current-session lookup failed. Two behavioral tests failed before implementation.

Acceptance: real running topic and phase-directed navigation; primary card precedes optional setup; reload/error never treats an unverified local ID as a valid checkpoint; empty selection remains explicit; keyboard/narrow layout and existing start/review offer continue to work. No confidence requirement, autoplay or new teaching policy.

Verification: 186 frontend tests, full lint/types and production build pass. Isolated Chromium Home journeys at390/800/1280px plus existing session-clarity journey pass (4 cases). Required code/pedagogy review reports no blockers/majors. Backend unchanged; latest full baseline421 pass. Existing build chunk warnings remain; session-clarity journey logged a duplicate-key warning outside this Home slice, queued for diagnosis. Manual VoiceOver and owner comprehension remain unverified. This does not complete Q1's broader empty/onboarding/project-checkpoint work or establish owner comprehension.
