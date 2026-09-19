# 0003 — Hint-first everywhere; explicit explanation default; Socratic/challenge opt-in
Date: 2026-09-19
Status: Accepted
## Context
AuDHD research recommends explicit, literal explanation as default and Socratic questioning only opt-in. LxD research shows unguarded answer-giving harms learning (Bastani et al. 2025) and hint-scaffolded tutors preserve it (Kestin et al. 2025).
## Decision
Two orthogonal settings: (1) *scaffolding policy* — always hint-first, one step at a time, brief; (2) *questioning style* — explicit (default) or Socratic (session flag). Critical-thinking challenge modes are separate opt-in blocks. Mode never switches silently; the planner may *suggest* with an explained, undoable adaptation.
## Consequences
+ Satisfies both bodies of evidence. − Explicit mode still withholds full solutions; the UI must make "show full solution" an explicit, logged choice.
## Alternatives considered
Socratic default (rejected: AuDHD demand-avoidance/ambiguity cost); answer-first (rejected: learning harm).
## Evidence / sources
docs/research/adaptive-learning-report.md §A; docs/research/audhd-learner-report.md.
