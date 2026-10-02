# Assessment feedback history

Save the exact completed attempt feedback, submitted answer, visible question/options and grading result in the existing answer library. Reference the original attempt; reopening/retrying the history save must never regrade, reschedule review or add competency evidence. Snapshot through the shared Grader so assessment, challenge, code and listening paths use the same behavior. Exclude personal assessment feedback from default suggestions and automatic reuse. Show historical grading details separately from current mastery; source passages not captured remain unknown. Save failures preserve returned grading results and offer signed save-only retry. Existing learning modes and optional confidence remain unchanged.

## Implementation and verification

The shared Grader finalizer writes an immutable TutorAnswer with surface assessment, original attempt ID, submitted answer, visible question/options, returned grading details and skill/area labels. Raw MCQ submissions remain in the snapshot; the UI shows their selected option text. It stores no hidden grading key and makes no claim about missing historical source passages. All four result surfaces (lesson, challenge, code, listening) expose the existing save status/retry control. History has an assessment filter, readable historical criteria/method, and read-aloud includes the question.

Personal assessment rows join the shared automatic-reuse exclusion query, so history remains accessible without promoting individual feedback as a general answer. Reopening or recovering a save invokes no grading, scheduling or evidence write. Save failures before/after commit preserve the grading response and issue signed save-only recovery; empty feedback returns the result with an explicit history warning rather than failing the completed grade.

- Full backend608 and frontend282 passed. Subsequent focused backend5 covers original question edits, both API entry points, suggestions exclusion, repeated save-only recovery before/after commit, MCQ display and empty feedback.
- Focused UI14 passed, including new historical-details coverage; lint/strict types and production build passed.
- Two isolated desktop/narrow browser journeys passed real deterministic grading → history → reload/filter, with zero POSTs during reopening.
- Independent code and pedagogy reviews found no blockers or majors. Browser fixture corrected to use role-based combobox lookup and support MCQ/cloze rotation.

## Limits

This does not add grading request idempotency, reconstruct historical questions for old attempts, or backfill missing feedback. A grading transport failure can still require separate request-recovery work; retrying a history receipt never regrades. Generated grades are not guaranteed correct. Personal feedback remains a past-attempt record, not current mastery. Broader real-material tutor quality and latency, ingestion and UX queues remain open.

Sanitized checkout verification: backend26 and UI14 passed. Final code review of empty-feedback handling and MCQ display found no blockers or majors.
