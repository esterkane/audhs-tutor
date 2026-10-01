# Saved answers in learning context

Preserve optional course, section and target identifiers supplied by the active local learning page, plus its visible target label and the learner's actual chat question. These identifiers scope history; they are not evidence that the backend retrieved or verified course material. Existing answers without identifiers remain in general history and are not guessed into a course. No new learning events or mastery writes. First implement and test request/snapshot metadata, then add scoped suggestions and context-preserving follow-up.

Status: implemented bounded contextual history. No new migration: bounded optional request fields are stored in existing snapshot JSON. Generic tests only; no private course titles or content in fixtures.

Implemented: optional course/section/target/label metadata and separately stored learner question; exact owner-scoped filters; guided section, task notebook and saved notebook wiring. Uploaded arbitrary notebooks do not inherit course scope. “Previously answered here” loads at most five exact-target replies on explicit opening, with dates, warnings, retry/empty states and links to scoped history. Saved replies invalidate history queries. Current context IDs are client navigation metadata, not verified source evidence; old records are not backfilled by guessing. Notebook targets include the source-content hash and cell position, so changed/reordered source notebooks do not silently reuse the same target.

Validation: 211 frontend tests, TypeScript, four isolated Chromium desktop/narrow journeys pass. Independent code/pedagogy review has no blockers/majors. 436 backend tests and lint/build pass. Test helper now keeps its QueryClient/router wrappers during rerender (previous helper dropped them). No migration needed.

Remaining: course/area-wide suggestion overview, verified manifest ID validation, answer freshness/corrections and linked follow-up chat. This is contextual history, not a claim that the earlier reply is universally correct.
