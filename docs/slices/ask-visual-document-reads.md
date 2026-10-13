# Ask visual document reads

## Problem and implementation
Ask still uses bounded generation history to select diagrams. Preparing editing and
archive controls requires a document library independent of generation attempts.
GET /api/authored-visuals now accepts an optional bounded answer_id, validates an owned
Ask answer and returns documents whose latest owned version targets that answer.
Archive state, stable pagination and existing unfiltered listing remain available.
Repeated versions do not duplicate documents. Unknown/foreign/non-Ask answers share
an unavailable response. No inference or source revalidation is needed to list history.

Inspection also found edits could change their target. The transactional save now
rejects a different target kind/ID before altering revision or inserting history.
A separate document is required for a different target. Existing retargeted history
is retained; listing matches its current target only. No database migration.
Generated API types include the filter. No learning/assessment/scheduling changes.

## Verification
28 focused history/command tests pass, including archive/restore, separate answers,
multiple versions, manual documents without generation requests, pagination, foreign/
missing/non-Ask targets, invalid filter length, legacy target history and rejected-edit
rollback. Code/provenance review found no blockers or majors.
Full backend suite: 1557 passed, three existing dependency warnings. Full lint,
Python/frontend type checks and API generation pass. No UI runtime code changed;
prior UI tests are not claimed as coverage for the still-pending document controls.

## Remaining
UI still reads generation requests; this prerequisite alone does not hide archived
items or open edited versions. Next implement document/version navigation and explicit
archive/restore with request recovery, then structured editing. Browser/keyboard and
responsive gates apply to those UI changes. See the document navigation design plan.
