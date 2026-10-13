# Provisional outcome and HTTP replay

2026-10-13. AssessmentOutcome explicitly combines the unchanged historical AttemptResult with ProvisionalFeedbackResult. Submission/challenge/finish/continue response declarations and request lookup accept the union. Recovery checks the provisional discriminator, reads the learner-owned immutable record and verifies its exact saved outcome. Grader return annotations widen, but no model route or learning write behavior changes.

23persistence/request tests pass including real HTTP completed provisional replay without score/correct/mastery/review fields, plus existing recovery regressions. Targeted Ruff and mypy (five source files) pass. No model calls or live records created.

Activation remains blocked on implementation work, not owner approval: generated OpenAPI/frontend types, all learner surfaces, provisional revisions, saved answer/help/source handling and non-pass continuation must be integrated before routing model results here. Current production grading still returns historical assessed outcomes; schema-only HTTP fixture is not proof of the full learner flow. No visual/browser claim for this backend-only change.
