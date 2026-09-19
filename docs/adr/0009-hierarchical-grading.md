# 0009 — Hierarchical grading with structured evidence
Date: 2026-09-19
Status: Accepted
## Context
Routing every assessment to an LLM is slow, costly and inconsistent. Bare scores are not evidence.
## Decision
Grader order: deterministic (MCQ, numeric, schema validation, code tests) → rule/rubric checks → local LLM → hosted model, escalating only when the previous level is insufficient or low-confidence. Every LLM grade returns `{criterion_results:[{criterion, passed, evidence}], misconception?, confidence}` validated by schema; the kernel converts results into `competency_evidence` rows with weights by grader level and confidence. Confidence rating is collected from the learner before feedback. Feedback wording is literal and non-punitive.
## Consequences
+ Cheap, fast, auditable grading; evidence quality tracked. − Rubrics must be written per assessment kind.
## Alternatives considered
LLM-only grading.
## Evidence / sources
Review brief §11; adaptive-learning report §B (calibration).
