---
name: audhs-visual-specs
description: Implement versioned inline visual explanations and diagram exercises in AuDHS using the reconciled V queue. Use for visual schema, rendering and interaction changes, not the audio visualizer.
---

Read docs/VISUAL-LEARNING-QUEUE.md and latest HANDOFF; resolve V task dependencies and existing ADRs. The uploaded kit's fixed decisions are not owner approvals. Reuse LearningObject/Representation boundaries without applying cache deletion semantics to authored immutable versions. Preserve learner scope, original source/version references and model/prompt provenance.

Use typed discriminated specs with bounded sizes and explicit semantics. Do not invent connections to force graph connectivity; cycles and multiple valid orderings require type-specific rules. Kernel selects eligible kinds and learner chooses whether to show a visual. Version edits, acceptance and retries must be explicit and idempotent. One server-owned repair budget covers schema and browser failures; cancellation/stale callbacks cannot generate again.

Render inline, lazily, using existing libraries first. No arbitrary authored HTML/JS/SVG, remote loader or model-supplied executable UI. Trusted renderer output still needs security settings, limits and failure tests. Provide text equivalent, keyboard selection/reorder, source access, reduced motion and fallback. Parse success is not semantic correctness.

Exercises require checked derivation, alternatives/partial orders where applicable, contestable feedback and separate preference/outcome signals. Confidence stays optional; never gate reveal or stop. Use feature-slice's required code/pedagogy reviews, sandbox browser journeys and exact verification evidence. New libraries need current primary-license/version and measured bundle checks; do not install a whole proposed stack.
