# Provisional feedback contract foundation

2026-10-13: owner approved future model-checked explanations as provisional feedback without mastery/review effects. Audited grader, staged execution, request recovery and saved-answer boundaries; reviewed design/PROVISIONAL-FEEDBACK-CONTRACT.md defines separate storage/outcome, atomic application policy, legacy staged handling, historical replay and all-surface continuation.

Added isolated strict ProvisionalFeedbackResult schema with content/session/assessment binding and advisory criterion observations. It rejects assessed fields and passed flags. No production caller, migration, routing or UI change yet.13schema tests pass; targeted Ruff/mypy pass. Code/pedagogy contract reviews passed. These tests verify shape separation, not persistence isolation or model accuracy.

Next: separate learner-owned storage, migration and backup/wipe; then atomic persistence/recovery and outcome union across all consumers, then learner UI/browser acceptance. Policy enforcement is NOT active. Do not claim completed approval as deployed protection. No model calls or new dependencies.
