# Explicit starter-code assistance

2026-10-04. C3 lesson experiment improvement.

## Problem and implementation

The lesson experiment had no direct starter request or way to bring an example into the editor. The baseline lesson journey passed but exposed only chat/hint controls. Suggest starter code now sends an explicit request through the existing lesson/source/recovery path. It asks for a small standard-library example, labeled invented data and a remaining learner task; these are model instructions, not verified guarantees. Unsent learner questions stay in the input and the chat displays a concise request.

Complete, explicitly Python-tagged examples offer optional append below existing code. No overwrite or execution occurs. The combined editor limit is enforced; immediate duplicate insertion is disabled. Undo restores the prior code only while the editor still matches that insertion exactly. Later edits are never overwritten by Undo. Existing output becomes stale through the existing code-identity check.

## Verification

11 focused frontend tests pass in both checkouts. Lint/types/build pass. Isolated browser journeys pass at390/1280 in both checkouts: starter payload, retained unsent question, source/code recovery, keyboard insertion, preserved existing code, unchanged not-run output, duplicate button disabled and Undo. Narrow screenshot inspected; visible request shortened after inspection. Code and pedagogy reviews found no blockers/majors. No new libraries, backend, routing, assessment or learning-state changes.

## Remaining limits

Undo is temporary and does not survive leaving/reload, while inserted code uses existing saved-draft recovery. Only complete Python/py fenced blocks up to16,000 characters and up to3 eligible blocks are offered; other responses remain readable/copyable. With several blocks, numbered insertion controls still require matching their order in the reply; a closer per-block control is a minor follow-up. The combined code may require learner edits before running. No execution correctness, source entailment or model compliance was established by fixture-based browser tests. Local-model grounding evaluation remains next, followed by the remaining C workspace phases.
