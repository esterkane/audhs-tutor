# Lesson evidence snapshot helper

2026-10-04. C3 backend prerequisite; not yet connected to live requests.

The helper retains whole passages using existing quarantine and context budgets. Blank/duplicate hits are excluded, retained raw text is hashed for corpus freshness checks, and the snapshot identity tracks ordered text, source labels, flags, trust, lesson goal and contract version. Ranking-score jitter does not invalidate otherwise identical evidence. Widening scope stays explicit, preserving cross-course discovery.

Quoted output escapes text, citation labels and flags. Original stored text/labels remain unchanged. Search traces and model-visible evidence are deliberately distinct: only retained passages belong in the eventual response sources.

Verification: five new tests plus existing untrusted-content/retrieval tests, 11 passed; Ruff and targeted mypy passed. Independent read-only review found no blockers/majors. No UI, model routing, learning logic, dependencies or database changes. Browser/keyboard/responsive checks are not applicable to this unused backend helper.

Remaining: wire server-resolved lesson context and retrieval, persist trace/snapshot, compare evidence on reuse, introduce grounded prompt/disclosure and render typed sources together. No grounded tutoring claim is made by this change. Retrieval trust filtering, corpus freshness, error/cancellation handling and persistence remain integration responsibilities. Directly constructing LessonEvidence is not an authorization or validation boundary.
