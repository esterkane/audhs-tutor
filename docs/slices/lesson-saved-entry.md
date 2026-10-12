# Open existing explanations from a lesson

Learners can open prior database-saved explanations for the active concept before
requesting another generated answer. A secondary shared Button/Link beside the
explanation controls opens existing /answers filtered by skill_id and surface=tutor.
The link is absent without a skill. Source-drift copy makes clear that this is history,
not a newly checked answer. No new cache, schema, endpoint, generation or learning
mutation. All modes use the same explicit action; primary generation remains available.

## Evidence
Inspected current Session controls and earlier browser render: no direct database
history entry existed there. Existing SavedLessonNotes is a separate tab-local archive.
Ten Session component tests pass, including exact skill-scoped URL and no unsolicited
tutor/audio generation. Two isolated browser journeys pass at320/1280: keyboard entry,
44px target, correct history filter, Back preserves unsent draft/checkpoint, zero API
writes, no horizontal overflow. Narrow screenshot inspected. ESLint, e2e types and
production build pass; existing large-chunk warning remains. Initial browser failure
was a getByLabel test selector; actual combobox exposes Show and selects tutor.
Code/pedagogy review found no blocker or major. No human-usability or latency percentile
claim. This avoids generation only when the learner chooses to read history; matching,
source freshness and automatic exact reuse remain separate. Empty history remains an
honest existing empty state. Logs:/tmp/saved-entry-{unit,build,browser-final}.log.
