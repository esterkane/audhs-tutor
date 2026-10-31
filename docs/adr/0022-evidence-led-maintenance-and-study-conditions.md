# ADR 0022 — Evidence-led maintenance and study-condition observations

Status: accepted for implementation under the owner's supplied learning-evidence review.

The supplied review is a research input, not an executable specification or a validated clinical
model. Preserve its caveats and the explicit-adaptation invariant. Do not infer diagnoses,
medication needs, burnout, mastery or failure from energy, attendance or productivity.

A reversible `planner.maintenance` preference defaults off. When explicitly enabled, future
plans contain brief cued recall and recap only; current plans are not rewritten. Explicit lesson starts ask the learner to disable maintenance first, before ending any saved session. A detector may
offer it after six completed sessions: the latest three on distinct days within fourteen days
all begin at energy <=2 and average at least one point below the preceding three. These are
conservative product thresholds, not validated burnout criteria. Missing sessions are not data.
Use existing proposal/decision/undo records and fourteen-day dismissal/never-suggest controls.
A current-session trial cannot apply a future-plan preference and is not offered for this card.

An optional, bounded next-start cue is an explicit preference. Recap and Settings can save or
clear it; Home surfaces it. It does not block finishing, alter recall evidence or replace notes.
It remains learner-owned private data in existing preference export/wipe/backup boundaries.

Optional study conditions use one append-only learner-scoped event and no new table. Recording
noise/presence/movement/timer choices is self-report, not automatic sensing or activation. The
summary joins a subsequent study event to later recall in a different session at least a day
later; unknown later study conditions invalidate earlier attribution. Repeated review of one
item is counted once. The latest 90 days/10,000 relevant events bound the summary. These are
observational associations, not randomized N-of-1 efficacy results or automatic recommendations.
Use the established experiment engine for controlled comparisons where treatment delivery can
be verified. No personal "best condition" is invented without actual delayed-outcome evidence.

FSRS remains the scheduler. No arbitrary requirement for exactly two or three successes is added
or substituted for mastery, and omission of confidence remains allowed. All reminders/timers,
novelty and sensory choices remain explicit, predictable, stoppable and optional.
