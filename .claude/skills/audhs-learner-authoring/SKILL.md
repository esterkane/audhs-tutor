---
name: audhs-learner-authoring
description: Implement optional learner capture, block editing, authored lessons and portable exports in the AuDHS A queue, preserving provenance and learning evidence.
---

Read docs/VISUAL-LEARNING-QUEUE.md and current curriculum/area, content-report, backup and Kernel interfaces. Map authored material into existing source/area semantics before adding parallel course tables. Distinguish origin from numerical trust tier; an authoring event is not mastery evidence.

Capture the exact content/version and source context with one action, no forced navigation. Preserve draft on failure, make repeated/retried capture idempotent and show save status. Use stable block identities, keyboard reorder and immutable version references. Archiving retains history; edits cannot silently change previously assessed content.

Tutor assistance is explicit and stored as draft. Publish is a distinct reviewed action; scheduling/indexing is idempotent and unpublish preserves past evidence. Keep note/model/source claims distinguishable and checks contestable. Reuse audhs-tutor-evidence for checks.

Interactive content uses validated templates, not arbitrary HTML/JS. Code runs only through existing explicit sandbox controls. Image/sketch dependencies stay deferred until selected; validate content/size/paths and provide text alternatives. Portable imports need safe paths, bounds, duplicate handling, asset/license provenance and a round-trip/backup-restore test. Keep authored learner content and raw assets out of the public repository. Follow required slice reviews and current publication policy.
