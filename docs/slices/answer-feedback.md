# Saved-answer feedback and visibility

Learners can label a saved response helpful, confusing, incorrect or outdated, add an optional reason and hide it from contextual lists. Preserve the immutable answer and all parent links. Labels are self-reports, not automatic verification, training or mastery evidence. General history exposes the report and permits reopening/restoring the item; contextual suggestions omit hidden/incorrect/outdated answers. A reported parent must visibly warn before future reuse.

Plan: separate owner-scoped feedback row keyed uniquely to the answer; revision-checked writes with repeat-safe same-state retry, defaults for old answers, learner export/wipe and backup tests. Explicit Save with draft recovery, server error/conflict handling and no optimistic claim of success. Then add source/version freshness checks independently; a matching source hash is not proof of correctness.

Migration preparation must happen outside the watched Alembic directory, then publish the finished revision atomically. The previous search migration demonstrated why an unfinished auto-generated revision must not be exposed to the development reloader.

Status: implemented and verified on disposable data; migration applied after a verified snapshot. Correction/replacement workflow and automatic source freshness remain separate follow-up work.

Evidence: 438-test backend suite passed before the additional simultaneous-write regression; two focused API/CAS tests then passed, including two independent sessions racing different reports (one saved, one 409). Full frontend suite: 219 tests; focused report/continuation regressions pass after the actual-parent warning fix. Four isolated desktop/narrow browser journeys pass. Independent code/pedagogy review major (warning targeted the opened answer instead of resumed parent) fixed and re-reviewed clear. Populated full/encrypted backup tests and two-learner export/wipe preserve/remove feedback appropriately. Final lint/types/build pass; existing bundle-size/WaveSurfer warnings remain.

The original answer remains immutable. API suggestions=true excludes hidden/incorrect/outdated reports; general history remains accessible. Current feedback is supplied as a learner report on explicit follow-up, with actual-parent warning and retry/loading gate in UI. This is not automatic model training, verified correction or source freshness detection. Report revision detects stale writes; identical retries return current state. Notes and visibility can be cleared and saved explicitly.
