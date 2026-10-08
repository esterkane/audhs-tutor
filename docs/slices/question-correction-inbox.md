# Read-only question correction inbox

R5 replacement-plan slice 1 discovery is implemented; resolution and editing are not. Preferences now offers a closed-by-default Reported questions section, separate from exclusions. It loads only on request and displays original wording, reasons, notes and current-content status. No mode/energy adaptation or learning event is introduced.

`GET /api/questions/corrections` is learner-owned, offset-paginated (20 default, 50 maximum), ordered by timestamp/id. SQL ranks non-withdrawn reports per target snapshot before filtering negative verdicts. A newer positive rating supersedes an older negative rating for that version; withdrawing it reveals the previous active rating, matching existing feedback semantics. This is not a resolved/unresolved workflow. Different question versions remain separate.

Only question wording is projected from snapshots; full item payloads, answers, keys and rubrics are not exposed. Current assessment content is compared with the original snapshot. Changed drafts cannot be safely mapped because legacy reports lack a question index; show the original, mark changed, and never guess another draft question. Missing/foreign draft content is unavailable. Notes and wording are rendered as text.

Read failure preserves a loaded page and states it may be stale. Refresh is explicit; no automatic retry. Pagination is disabled during reads and returns focus to the heading on success. Existing exclusions remain independently accessible. No model calls, dependencies, migration, mutation, grades or scheduler changes.

## Evidence

- 16 backend tests pass across correction discovery, existing question controls and area feedback: latest-rating/withdrawal semantics, ownership, bounded pagination, missing content, changed drafts, answer-key omission, no assessment attempts/state writes.
- Five frontend tests pass across inbox and existing controls: lazy loading, retained reports/retry, pagination/focus and unavailable status.
- Two real sandbox Chromium journeys pass at390/1280: synthetic report creation, Preferences keyboard entry, simulated503 refresh failure with retained content, explicit retry, disclosure and no horizontal overflow. Both screenshots visually inspected. Test reports withdrawn and sessions ended.
- Ruff, strict mypy (209 files), frontend lint/types and production build pass. Existing bundle-size warning remains.
- Bounded independent code/pedagogy review: no blockers or major findings.

## Remaining

No editing, resolved-state command or publication exists here. Next implement versioned correction proposal/preview after establishing the replacement ownership contract; do not label this whole R5 complete. Full screen-reader/human comprehension gates remain open. No claim that a reported question is incorrect solely because it received a negative rating.
