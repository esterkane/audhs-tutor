---
name: audhs-audit-slice
description: Implement bounded AuDHS Tutor audit fixes using finding IDs, current-code evidence and staged acceptance gates. Use for work from the UX technical audit, not unrelated projects.
---

# audhs-audit-slice

Read the target repository's AGENTS.md, CLAUDE.md, latest docs/HANDOFF.md and docs/AUDIT-IMPLEMENTATION-PLAN.md. Resolve the requested R-stage and its finding IDs. If no stage was named, select the earliest unfinished dependency and state the choice.

Reconcile each finding against current code and dirty changes. Classify audit-only, code-confirmed, reproduced, already-fixed-with-evidence or still-open; do not repeat stale fixes. For defects add a failing behavioral regression before implementation. A source pattern is not proof of an observed data-loss incident.

Create a bounded slice spec with story, state ownership, affected events, API/data changes, accessibility and observable acceptance cases. Follow existing .claude/skills/feature-slice/SKILL.md and path rules; use existing required code/pedagogy review workflows when applicable. If those review capabilities are unavailable, record review as pending rather than inventing clearance.

Preserve inherited work and newer visualizer behavior. Use local execution/fakes and isolated learner data. This skill grants no permission to publish live drafts, migrate live data, call paid providers, push, or expand browser/account access. Existing owner-only command conventions remain intact.

Finish with finding IDs resolved, exact fresh checks, limitations, migration/rollback notes where relevant, and a concrete next slice in shared handoff. Never mark an entire stage done from a partial slice. Use audhs-state-reliability for retry/transaction/recovery changes, audhs-content-correction for lifecycle/provenance, and audhs-learning-ux for the learner journey; read only those that apply.
