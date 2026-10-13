# Assessment and review parent visibility

Assessment visibility now requires both question ownership and parent-skill access.
A shared question or owned correction cannot expose another learner's private lesson.
The predicate uses an explicitly correlated skill subquery so joined snapshot queries
keep the same access rule. Practice eligibility remains a separate condition.

Review selection and direct snapshot reads require access to the card's required
skill and optional learning object. This applies to vocabulary cards as well: their
references still are not treated as assessment IDs, but cached text cannot bypass
private parent ownership. Direct snapshot reads also check any linked assessment's
visibility before mapping content. Suspended but visible history remains readable.

No producer, activation, model routing, scoring or scheduling policy is introduced.
Private answer-derived activation remains blocked. Broader direct ORM and storage
constraint work remains under PRIVATE-LESSON-ACTIVATION.md.

## Verification
16 focused assessment visibility/question-state tests pass: shared/owned question on
foreign skill, question snapshots, grader selection, cached vocabulary/assessment
cards, foreign object behind visible skill, and existing suspension/replacement rules.
Review found no blockers or majors, including SQL correlation and historical access.
Full backend suite: 1,584 passed. Lint/types pass. No UI changes, live
model calls or learner-state writes were used for verification.
