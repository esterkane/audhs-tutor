# Saved session questioning display

The lesson start card now uses the saved session questioning mode, followed by the
actual turn metadata when available. Socratic sessions say “Start with a question”
and describe preparing a question; explicit sessions keep their explanation labels.
The empty state, draft helper and listening helper use the same mode.

This changes presentation only. It does not change requests, model routing, histories,
future-session defaults or the per-session Socratic opt-in.

Verification: frontend TypeScript build and touched-file ESLint pass; existing session
unit suite 11 passed; bilingual saved-language/history and lesson-focus browser journeys
4 passed; knowledge-reading workflows 2 passed. Browser snapshots were inspected at
390 and 1280 pixels. No new tests mirror these low-impact copy changes.
