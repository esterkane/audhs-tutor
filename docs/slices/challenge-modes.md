# Slice: challenge-modes (Stage 2)

**Story.** Opt-in critical-thinking blocks: planted error, steelman, teach-back, calibration. Each is generated for the current skill, graded against a hidden key with per-criterion feedback, and always leaves a delayed review item.
**In/out.** `prompts/challenge/*.v1.md`; `orchestrator/challenge.py::start` (structured `ChallengeItem{prompt, hidden_key, criteria}` via `gen_items`, stored as `Assessment(kind=challenge_<mode>)` with a rubric; unattempted items are reused), grading through the hierarchical grader with the hidden key as reference (always LLM level), dimension per mode (application / transfer / explanation / recall), FSRS due forced to ≥ +2 days. `GET /api/challenge/modes`, `POST /api/challenge/start`, `POST /api/challenge/submit`. UI: `ChallengePanel` (four concrete modes, confidence before submit, criterion feedback, "Skip the challenge" always available).
**Events.** `attempted`, `graded`, `evidenced`, `reviewed` (delayed).
**Pedagogy.** Challenge is a separate opt-in block (ADR-0003); the hidden key is never shown before grading; feedback wording is literal.
**Verified by.** `tests/test_stage2_api.py::test_challenge_round_trip`, `frontend/src/features/challenge/ChallengePanel.test.tsx`, Stage 2 benchmark D with the real model.
