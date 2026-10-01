# Saved tutor answers and suggested questions

Status: queued by owner, 2026-10-01. Implement after current work; coordinate with Q2/Q3 and authoring A01 rather than create duplicate answer stores. Planning only; no database migration or feature activated.

## Requested outcome

Completed tutor answers are saved automatically in the local database, searchable after browser restart and visible as suggested question-and-answer pairs for each course. Retain cross-course knowledge-area navigation: a course is a filter/source reference, not a new learning silo. Opening a saved answer must not call a model again. Asking a follow-up remains available and creates its own linked answer.

## Current evidence

StudyTutor restores bounded conversation history from browser localStorage; that is not a durable searchable answer library. `TutorTrace` stores operational metadata and model/retrieval references, not the complete question/answer. `/api/playground/tutor` returns text and a turn_id. Reconcile the session text, voice, representation and feedback paths before choosing the shared persistence boundary. Do not assume old answers can be reconstructed from metadata or re-generate them as if they were historical records.

## Design requirements

- Save learner-scoped question and delivered answer, turn/request identity, creation time, model/prompt version, answer mode, course/area/lesson/notebook-step references and source/version citations. Use stable IDs, not a displayed title alone. Preserve relevant code/answer/output snapshot references for context-dependent feedback; do not label stale code advice as generally reusable.
- SQLite is authoritative; start with local full-text search and scoped indexes. Semantic search is a later measured extension, not a prerequisite or automatic Qdrant duplication. No paid-model calls for listing/searching existing answers.
- Store completed answers idempotently. Interrupted/partial output may be retained for recovery but must not appear as a complete suggested answer. Save failures remain visible without losing delivered text, and retry cannot duplicate records. Database commit and stream completion ordering need explicit tests.
- Suggestions come from real completed answers relevant to the current course/area/step. Show a concise question, answer preview, sources and date; open full answer and continue chat. Explain when no saved answer exists. Generated suggestions without answers must be separately labeled, never passed off as previously answered.
- Store the learner's real question separately from internal action prompts such as Explain this step; derive a meaningful display label using target metadata without inventing what the learner asked. Context-dependent personal feedback is not automatically a generic FAQ.
- Support helpful/unhelpful, incorrect/outdated and optional reason; reuse correction/report infrastructure. Allow hiding/removing from suggestions and reviewing prior versions. Corrected answers retain provenance and version relationships. Keep labels/preferences separate from mastery or independent assessment evidence.
- Opening/accepting an answer does not verify its truth or change mastery. Source edits, removed material or changed notebook code can mark it stale. No automatic feedback loop treating the tutor's earlier answer as independent factual evidence.
- Private answers, code/context and database snapshots remain private under existing publication policy. Include the library in private learner backup/export with scoped restore tests; exclude real Q&A from public fixtures and search demos. Do not retain unnecessary credentials or unrelated full notebook content.

## Queued tasks

| ID | Task / dependency | Acceptance evidence |
|---|---|---|
| QA00 | Map every answer path and draft storage/lifecycle ADR | Coverage matrix for lesson, notebook/playground, answer feedback, representations and voice; ownership, context IDs and relation to authoring/correction decided. |
| QA01 | Durable answer persistence; QA00 | Migration/restore on disposable data, learner isolation, exact text/source snapshot, duplicate request and failed-save recovery tests. Completed vs partial state explicit. |
| QA02 | Local scoped search and retrieval; QA01 | Course/area/step filters, full text, pagination, deleted/stale states, cross-learner denial; opening a record makes zero model calls. |
| QA03 | Suggested Q&A on course/area learning pages; QA02 | Relevant previously answered list, useful display labels, full answer/source view and follow-up preserving context; empty/loading/error, keyboard and narrow-screen journeys. |
| QA04 | Corrections and reusable-answer rules; QA03 | Report/hide/replace workflow, source/code freshness, no stale personal feedback suggested as general advice, idempotent votes, no mastery changes. |
| QA05 | Backfill/portability; QA01–QA04 | Import only real available browser/history records with provenance and consent for scope; no fabricated history; encrypted backup/export round-trip; sanitized public check. |

Use existing `audhs-tutor-evidence`, `audhs-state-reliability`, `audhs-learning-ux` and, where capture/versioning overlaps, `audhs-learner-authoring`. No new skill needed solely for another queue entry.

## Execution prompt

```text
Implement the next dependency-ready QA task in docs/TUTOR-ANSWER-LIBRARY-QUEUE.md. Read latest HANDOFF and existing Q/authoring plans. Reconcile current response/event/storage paths first. Save actual completed answers locally with stable context and provenance, keep partial/stale/disputed output distinct, and expose local course/area-filtered search plus relevant saved question suggestions. Reuse existing routing, correction and backup boundaries; do not regenerate history or index model answers as independent source truth. Add behavioral failure/isolation/idempotency tests and required code/pedagogy review. Follow current paired publication policy with only synthetic data in public. Leave later tasks queued and record exact verification/limitations.
```
