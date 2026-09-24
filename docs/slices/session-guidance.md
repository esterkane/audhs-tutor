# Clear session guidance

The learner can identify the current activity, what to do now and what happens next.
Show learn → question → continue guidance; collapse plan settings, extra representations and score details.
After feedback, continuing the plan is primary; another question is explicitly optional. Keep stop/recap available.
Review explains recall → confidence → reveal → rating; recap explains the final two ratings.
No API, planner, grading, event or automatic mode changes. Keyboard-accessible native disclosures; no motion.

Reproduction: the teaching screen exposed explanation, hint, summary, representations and switching alongside plan/energy controls. Assessment feedback promoted “Next item”, making the stopping point unclear. Review did not explain where to answer. These are guidance and action-priority defects, not missing learning mechanics.

## Acceptance and verification

- Current activity and learn → question → continue instructions: Session regression test and browser inspection.
- Plan/energy and extra learning controls collapsed: component regression; native keyboard-operable details.
- Confidence required before feedback; grading failure retains input: existing and new Session regressions.
- Continue after feedback uses the existing server transition; another question is optional: new regression.
- Review/stop/resume/reload boundaries: all 7 sandbox browser journeys passed.
- Accessibility: axe passed on the assessment screen. Full lint, 339 backend and 53 frontend tests passed. Final presentation adjustments rechecked with TypeScript, ESLint and Session tests.

## Review fixes

Code and pedagogy reviews found no blockers. Fixed cloze-specific instructions, qualified persistence wording (unchecked text is not saved), and kept experiment assignment visible. Soft timer remains below the current activity; source descriptions and answer metadata stay inspectable in disclosures. The explanation action becomes secondary after an answer, leaving the question as primary.

## Limits

This is a bounded session-guidance improvement, not a full redesign of Home/navigation or the challenge/practice panels. No tutor prompts, grading decisions, planner rules or live learner records changed. Unsubmitted text is still not persisted when leaving; the UI states this explicitly. The existing stop-during-grading lifecycle remains a follow-up for draft persistence/concurrency work. No learner usability study or learning-outcome claim is made.
