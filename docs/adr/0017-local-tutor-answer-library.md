# 0017 — Local tutor answer library
Date: 2026-10-01
Status: Proposed

## Context

The owner requested saved, searchable tutor Q&A and course-specific suggestions. Current browser history and trace metadata do not implement this. QA00 inventory in `docs/design/tutor-answer-lifecycle.md` identifies shared text/voice producers, existing representation and assessment stores, missing workspace scope and explicit commit requirements.

## Decision

Propose one learner-scoped SQLite answer library, implemented through a shared persistence service called by response producers, not the model gateway or each transport independently. Keep the Learning Kernel authoritative for progress. No hosted-model search, extra vector database or automatic training on prior answers.

An answer has immutable question/response text, bounded context/version snapshot, source references, model/prompt metadata, parent relationship and completion state. Separate mutable visibility/helpfulness/dispute state. Link existing assessment attempts and representation versions instead of replacing their stores; snapshot delivered representation content because cache invalidation deletes the original row. Use local FTS for completed, visible entries; course/area/step filters use validated stable references.

Use a unique learner + surface + request intent key with a canonical payload fingerprint. Same key/same payload replays the persisted result; different payload conflicts. Database constraints handle concurrent saves. Generation itself is not guaranteed exactly once by this constraint: an in-flight duplicate must return an explicit pending/conflict state rather than start another model call. Do not hold a SQLite write transaction during inference.

Persist a successful response before announcing saved completion. If persistence fails after tokens were delivered, retain those tokens and signal unsaved/partial recovery explicitly. Never silently display Saved. Recovery must not trust arbitrary client text as a verified historical model answer. Model-call billing/audit commits remain independent. Delivery acknowledgement, if added, means received by client, not read or understood.

Suggestion eligibility requires complete, nonempty, visible, current-enough content scoped to the target. Personal code/assessment feedback appears in history with context rather than general suggestions. Reopening makes no model call, changes no mastery and adds no independent factual evidence. Follow-up is a new linked turn.

## Consequences (positive / negative / follow-ups)

Durable local reuse reduces repeat requests and keeps provenance. It adds private stored content, lifecycle/retention obligations, migration/backup tests and scope identifiers to workspace requests. Partial/stale/disputed records need honest UI. Existing historical trace metadata cannot reconstruct prior answer text; backfill is limited to actual available records with provenance.

QA01 must prove ownership, idempotency, commit/stream ordering, save failure and deletion behavior. QA02 adds scoped FTS; QA03 surfaces suggestions; QA04 handles corrections; QA05 validates bounded historical import and backup round trips. No live migration is part of this proposed record.

## Alternatives considered

- Browser history only: cannot meet database search/restart/backup requirements.
- Store everything in TutorTrace: conflates operational traces with user-visible content lifecycle.
- Persist at ModelGateway: captures nondisplayed/internal output and loses course/UI intent.
- Index generated answers into course corpus: risks treating model assertions as source truth.
- Regenerate missing history: not a record of what was answered.

## Evidence / sources

Local paths and behavior inspected in `docs/design/tutor-answer-lifecycle.md`; owner requirements in `docs/TUTOR-ANSWER-LIBRARY-QUEUE.md`. This proposal changes no existing binding decision or runtime behavior.
