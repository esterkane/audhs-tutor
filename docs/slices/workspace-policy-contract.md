# Workspace policy composition — 2026-10-15

## Problem and change

The workspace concatenated shared session pedagogy requiring representation prefixes and hint-first interaction with a task requiring direct explicit explanation and no unsolicited prefixes/quizzes. Source inspection confirmed the conflict; local samples exhibited the unwanted behavior.

A cached workspace-only base now carries common safety, source, language and evidence boundaries. Existing workspace task contracts remain authoritative for explicit/Socratic behavior, hint withholding, full-solution requests, formative feedback and starters. The shared session/grader base is unchanged. This scoped exception to the older no-fork convention is documented in the prompt rules; it is not a general prompt rewrite.

Effective prompt identity is `playground.tutor.v15+workspace.v1`, including grounded/count/starter variants. Old exact saved replies cannot silently replay under the new identity. Historical answers remain available as history. No migration, frontend, provider routing, competency, grading or scheduling change.

## Verification

70 affected backend tests pass: grounded/ungrounded composition across explicit/Socratic and explain/hint/check/starter, source honesty, stale-output boundaries, response persistence/streaming and old prompt replay rejection. String-level contracts establish composed instructions, not compliance or semantic truth.

Two actual local Gemma12 replies used identical frozen follow-up requests to the earlier baseline. Unwanted representation prefixes and quizzes were absent. The explicit replacement correctly computed40/(40+60)=40%. The ambiguous case still assumed the original total without acknowledging the alternative. This is evidence for the bounded presentation-contract correction, not a quantity-reasoning fix or general accuracy claim. Raw report remains private. No hosted calls or routing changes.

Independent code review cleared composition/caller scope and answer identity. Pedagogy review cleared retained safeguards and the full-solution check exception, with the ambiguity limitation explicit. No UI files changed; prior re-entry visual/keyboard/responsive evidence is unchanged rather than claimed as a new prompt-semantic test.

## New teaching direction

The owner's supplied dialogue is reconciled in `docs/design/LEARN-TOGETHER-CONTRACT.md`: respond to the learner's reasoning, provide enough explanation before questioning, preserve real-versus-hypothetical boundaries, restore context when confused, and connect reasoning to practical work. This policy slice does not implement those stages or silently enable guided Ask mode. Source claims and reported calculations in the private reference remain unverified.

Final boundary checks:24 additional saved-answer/lesson-memory/starter tests pass; full lint/type checking passes. These complement the70 affected tests above. No new frontend build is required for this backend/prompt-only delta.
