# Replacement visibility and resolution inventory

2026-10-08. Read-only implementation investigation at private commit f737c3c. No ownership migration or replacement publication is implemented by this document. Existing assessments are shared; these are release prerequisites for introducing private replacements, not evidence of a current cross-owner leak.

## Separate contracts

1. `visible(learner_id)`: shared assessment OR matching owner. With no learner context, shared only. This is access control, independent of suspension.
2. `eligible(learner_id)`: existing practice-state rule. Do not silently combine visibility with this predicate: challenge exclusion detection negates it. Use visible AND eligible for selection, visible AND NOT eligible for exclusion checks.
3. Canonical content creation/deduplication: shared-only, even for the owning learner. Resolve that canonical identity into an owned replacement only at future-practice entry. Otherwise private corrections may suppress shared generation or become global exercise/check templates.
4. Future-practice resolver: same learner, compatible kind/skill, terminal accessible identity, bounded traversal/cycle rejection. Return identity, text and token from the same resolved snapshot.
5. Historical/receipt reads: enforce receipt/session ownership, retain exact original identity, never resolve forward. Completed retries return their original result before current practice eligibility validation. Pending old work must conflict rather than silently target a replacement.

## Current path matrix and required changes

| Surface | Inspected implementation | Required ownership/resolution gate |
| --- | --- | --- |
| Ordinary selection / session preview | orchestrator/grader.py `next_item`; api/sessions.py Assessment query | Visible AND eligible; resolve future identities without duplicate chain endpoints. |
| Shared seed / curriculum publication | kernel/seed.py assessment queries; kernel/curriculum.py publication duplicate scan | Shared-only canonical queries; owned correction must not suppress seed or shared publication. |
| Challenge reuse and generation guard | orchestrator/challenge.py `existing`, `reusable` | Positive selection visible AND eligible; excluded guard visible AND NOT eligible. An unrelated owner's private row must neither be selected nor block generation. |
| Code canonical exercise and check creation | kernel/exercises.py `ensure_exercise`, `ensure_check_item` | All initial and post-commit race/dedup queries shared-only; resolve at caller with learner identity. |
| Code entry / linked check | api/exercises.py `_view`, `for_skill` | Resolve primary and linked check independently; matching check ID, text, token. Preserve stored canonical exercise JSON. |
| Code hints / solution | api/exercises.py `_exercise`, `hint`, `solution` | Check visibility before returning hints/solution. Current solution check text comes from exercise JSON, whereas `_view` reads linked assessment text: unify future check resolution without mutating historical snapshots. |
| Listening task cache and post-create race | kernel/listening.py `existing_task`; orchestrator/listening.py `ensure_task` | Shared-only canonical clip lookup, then learner resolution before active check; never reuse another owner's private content or generate around an exclusion. |
| Listening validation | kernel/listening.py `validate_task` | Ownership and eligibility under lock before changing validated metadata. Keep source/clip association. |
| Direct assessment refresh / grading content | api/assess.py `refresh_item`; orchestrator/grader.py `versioned_view`, `grade`; orchestrator/assessment_content.py `snapshot`, `validate_new`, `guard_write` | Central snapshot visibility, including calls without learner context; future entry may resolve, submitted IDs never do. Detached grading inputs must retain the original identity. |
| Review queue/count/priority | kernel/question_state.py `review_eligible`; kernel/memory.py; api/sessions.py | Visibility for assessment-backed references, keeping explicit vocabulary exceptions. Superseded cards are excluded, not retargeted or rescheduled. |
| Review display/rating | kernel/review_content.py `snapshot`; api/review.py; kernel/review_requests.py | Do not merely filter the LEFT JOIN: a denied assessment can otherwise fall back to prompt_json. Explicitly reject an inaccessible assessment-backed reference before display/rating. Preserve completed owned receipt replay. |
| Question status / exclusions | kernel/question_state.py `read`, `transition`; api/questions.py preview/list | Visibility independent of state; foreign private IDs return unavailable, not default-active. Excluded list/count must not reveal inaccessible question metadata. |
| New reports / correction authoring | kernel/question_feedback.py `record`; kernel/correction_drafts.py `original`, create/inspect; api/correction_drafts.py source | Require visibility before snapshotting answers/rubrics or creating reports. `original` currently has no learner argument; pass identity explicitly through all callers. |
| Existing report inbox | kernel/question_corrections.py `inbox` | Keep owned immutable report snapshot; current-content comparison must not read inaccessible current rows. Do not resolve report identity into a replacement. |
| Attempt/review recovery | orchestrator/assessment_requests.py; db/workspace_requests.py; kernel/review_requests.py | Existing completed receipt wins before new validation. Never rewrite request/body/fingerprint or assessment ID. Test recovery after predecessor supersession. |
| Portability | db/portability.py export_learner/wipe_learner | Discovery filters only learner_id. Explicitly include owner_learner_id assessments and their owned rubrics, then remove dependencies before owner rows. Restrictive ownership FK; no SET NULL. Preserve shared and other-owner content. |
| Backup/restore | db/backup.py | Whole-installation snapshot is distinct from per-learner export. Round-trip ownership, lineage and receipts into an empty target; migration and FK checks. A learner-scope backup is not a public sanitized snapshot. |

## Next coherent implementation

Implement the ownership foundation as one reviewed change: nullable restrictive owner foreign key/index, separate visibility/shared predicates, all query/direct-read gates above, and export/wipe handling. Do not enable an endpoint that creates replacements yet. Test two learners and shared content across every surface before proceeding to lineage/resolver and atomic publication. Review the proposed ADR-0019 contract before schema work; this inventory is not ADR acceptance.

Minimum fixtures: shared active/suspended, A-owned active/suspended, B-owned active/suspended; absent learner context; primary/linked code IDs; vocabulary reference colliding with private assessment ID; assessment-backed review with cached prompt text; owned correction matching a canonical seed/clip/exercise; completed old receipt and pending old submission. Tests must assert both denied content and absence of unintended generation, evidence, hint events and schedule writes.

Then implement lineage/resolution and final publication impact preview (review counts, linked consumers, source passages, retained history), followed by atomic publication and integrated sandbox acceptance. No live curriculum publication is authorized by implementation tests.

## Evidence and limits

Inspected concrete Assessment queries/direct gets and snapshot callers under backend/app, plus canonical race rechecks and portability implementation. No runtime changes, model calls, live data mutations or test-pass claims. This is a reviewed inventory, not proof that future ownership enforcement is complete. Dynamic/raw SQL and new consumers must be rechecked with the migration diff; executable two-learner coverage is the release gate.

Bounded architecture review found no concrete contradiction or major omitted blocker; enforcement remains unimplemented and requires the stated tests.
