# 0004 — Learner model: MemoryState (FSRS) separate from CompetencyState; mastery is a view
Date: 2026-09-19
Status: Accepted
## Context
One learner, sparse data. Remembering a fact (memory) is not the same as being able to explain, apply and transfer a concept (competence). Deep knowledge tracing needs MOOC-scale data. Four stored sub-scores at n=1 would be false precision.
## Decision
`memory_state` (per review item; FSRS difficulty/stability/retrievability/due) is owned by the FSRS scheduler. `competency_evidence` rows (per skill, dimension ∈ recall|explanation|application|transfer, score, weight, source attempt, ts) are produced by assessments. `competency_state` is a kernel-refreshed materialized view: per-dimension weighted mean with time decay, evidence_count, confidence (grows with count and agreement), last_demonstrated_at. The recall dimension additionally ingests mean FSRS retrievability of the skill's items. Mastery (for the map and gating) = f(competency_state, prerequisites). New-material gating uses competency + prerequisite graph; review scheduling uses memory only. An open learner model exposes both.
## Consequences
+ Interpretable, undoable, low-data; evidence can be re-weighted without migration. − Two states to explain in the UI.
## Alternatives considered
Single mastery score (rejected: conflates memory and competence), DKT (data-hungry).
## Evidence / sources
docs/research/adaptive-learning-report.md §A, §C; review brief §2.
