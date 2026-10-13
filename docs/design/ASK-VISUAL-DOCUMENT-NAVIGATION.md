# Ask visual documents: editing and archive integration

Status: read-path prerequisite implemented, UI stages pending, 2026-10-13. Follows the accepted authored visual
lifecycle; no new learning or publication policy. This records a prerequisite found
before adding edit/archive buttons. Read-path implementation evidence is in ../slices/ask-visual-document-reads.md.

## Concrete current problem

`frontend/src/features/ask/AnswerVisual.tsx` selects from the latest 20 generation
requests and reads each request's immutable `result_version_id`. It never reads the
current document state. Consequently:

- A future edit would save version 2 but reopening this panel would still show the
  generation's version 1. Changing the generation receipt would destroy its meaning.
- An archived document remains reachable through its completed generation request;
  simply adding an archive command would not hide its diagram here.
- Documents older than the 20-request window cannot be found here, even though their
  versions remain stored. Failed/cancelled attempts consume that window too.
- The display unconditionally says “Model-generated draft”, although version detail
  already provides server-owned origin. That label would misdescribe learner edits.

The backend already separates these responsibilities:
`kernel/visual_history.py` lists documents by owner/archive state and versions by
immutable version number; `api/authored_visuals.py` exposes those reads. Its document
list has no answer filter. `schemas/visual_history.py` exposes revision/archive state
but no latest-version pointer. `kernel/authored_visuals.py` rejects edits/reviews of
archived documents and serializes commands with revision checks and replay receipts.
Generation history is execution history, not the authored library.

The live `/ask` entry is reachable and has the expected composer/navigation. No live
answer was generated or learner data mutated for this audit. Existing sandbox tests
cover generation/review flows, but their single-version fixture cannot establish
edit/archive navigation correctness. Those scenarios must be added before release.

## Smallest coherent implementation sequence

### 1. Answer-scoped document reads

Extend the bounded existing document list with an optional exact Ask answer target
filter. Validate ownership of the requested answer; never expose another owner's
existence or return a whole-library fallback. Match the latest owned version with `target_kind=answer` and exact `target_id`,
avoiding duplicate document rows and historical-target matches.
Retain the existing archive filter, stable ordering, offset and limit bounds.

Inspection found save previously permitted retargeting. Edits now retain the latest
version's target kind/ID; a different target requires a separate document. The read
filter uses current-target membership, so legacy retargeted history does not surface
a document under its former answer. Historical content remains unchanged. No new
latest-version pointer or migration is required.

Use the existing bounded versions endpoint to select the latest version and explicitly
browse older versions. Do not add a migration merely to avoid one bounded read.
Generate API types and test ownership, answer filtering, duplicate versions,
archive state, pagination and documents without generation requests.

### 2. Separate request status from saved diagrams

In AnswerVisual, retain explicit generation/start/cancel/retry controls and request
status. Add a document selector for saved diagrams of this answer, with explicit
pagination. Default to active documents. Keep a clearly labelled “Archived diagrams”
view so archive never removes the recovery path. Show saved document title and version,
not only request timestamps. Completed generation selects its document and refreshes
the library; reopening performs reads only.

Select latest version on opening a document; choosing a historical version stays
explicit until the learner switches it. A refresh must not overwrite an unsaved edit
or silently change a selected historical version. Label historical versions and
render their exact recorded origin, sources and reviews. Do not transfer old reviews.

### 3. Reversible archive and restore

Use existing archive commands and immutable request recovery with payload
`action, document_id, expected_revision, archived`. Fetch current revision before a
new intent; a retry uses the frozen original body/key. No automatic new-key retry on
409. Disable conflicting document actions while a mutation is uncertain, but keep
answer/chat and Stop waiting available. A cancelled HTTP wait is not a confirmed
server cancellation.

Confirmed archive hides the diagram from active presentation and offers Restore.
Preserve versions, review history, source provenance and unsent note/edit drafts.
Confirmed restore returns to the same document without regeneration. If refetch fails
after mutation confirmation, distinguish the saved action from unavailable refreshed
state; do not falsely report that the action failed or reapply a stale receipt as the
latest server state. Navigation/unmount guards must reject late UI callbacks.

### 4. Structured version editing

Use bounded fields for title, text equivalent, node labels/explanations and named
relationships. Maintain IDs and source references; no raw executable code editor.
A local preview is not a saved version or an accuracy check. Freeze the exact base
version/document revision with the draft and preserve it across navigation. Save uses
the existing version command, never overwrites historical JSON. On conflict retain
the draft and require explicit comparison/recovery rather than merging silently.
Backend validation remains authoritative. Derived material stays local after edits.
Historical versions remain read-only; starting from one must be explicit and preserve
provenance. No new model call is needed for manual editing.

## Expected files

Backend: api/authored_visuals.py, kernel/visual_history.py and focused history tests;
possibly command validation/tests only if the retargeting check finds an invariant gap.
Frontend: generated API types, AnswerVisual.tsx, focused document/action components,
useRequestRecovery.ts and recovery tests, ask-visual.spec.ts. Reuse the graph renderer,
tokens, disclosure and recovery components. No new library or learning-kernel change.

## Release evidence required

- Real command/read API tests with disposable SQLite: archive/restore preserves row
  counts, idempotent lost-response retry, stale revision, ownership and pagination.
- Sandbox browser: generate → edit → latest version on reopen; previous version stays
  accessible with its own review; archive → reload → archived view → restore.
- At least 21 generation attempts and an older document remain discoverable through
  paginated document history; failed attempts do not hide saved documents.
- Lost response, rapid repeated clicks, stale response after document switch, denied
  tab storage, unsaved draft retention and read failure after confirmed mutation.
- Keyboard selection/actions/focus recovery; 390px and desktop screenshots, reduced
  motion, enlarged text, no overflow and readable text when graph renderer fails.
- Assert no extra inference on reads/review/archive/restore/manual edit; no competency,
  assessment, FSRS, source deletion or public-export changes.
- Required code/pedagogy review, affected tests, full applicable suites/lint/build and
  dual private publication after a coherent verified implementation.

## Separate unresolved gates

Diagram semantic correctness remains unqualified after the local two-case trial.
Document navigation cannot fix that. Learning exercises must still use existing
reviewed objective/rubric contracts; presentation review is never learning evidence.
