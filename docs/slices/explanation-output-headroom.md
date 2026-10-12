# Text explanation output headroom

The learner should receive a complete worked example, not an answer cut mid-equation.
Two local Session-shaped comparisons hit the existing190-token explanation ceiling.
Increase only ordinary text EXPLAIN to384; keep the prompt's six-sentence instruction.
No schema, routing, source selection, context, assessment, mode or energy changes.
No UI alteration. Existing partial-output disclosure and safe replay remain mandatory.

One captured synthetic prompt with384 output allowance stopped naturally at305 tokens,
completing numerical examples. It still exceeded six sentences and is not a complete
teaching-quality pass. Raising the ceiling can increase completion latency and permitted
output usage; it is a completeness mitigation, not a latency optimization. Gateway budget
reservation continues to receive the actual ceiling. No hosted inference was performed.
Evidence:evals/results/explanation-ceiling-20261012.json.

Spoken explanations and language conversation retain190, Socratic120 takes precedence,
hints95, summaries160 and requested full solutions700 remain unchanged. Tests exercise
actual gateway arguments for all these cases. Existing partial/cross-transport recovery
checks ensure replay does not generate again or duplicate learning writes.

Verification:39 targeted orchestrator/recovery tests, Ruff and strict application
mypy228 pass. No frontend change; no new browser or visual acceptance claim. Code/pedagogy review
supports bounded headroom but explicitly does not certify quality or speed. Review edge
cases (typed language conversation and combined spoken/Socratic precedence) addressed.
No migration; rollback restores the prior text ceiling. Future work: evaluate concise,
complete explanations across subjects and reduce unnecessary template overhead without
removing the learner's requested context. Do not silently truncate a natural completion
to enforce sentence count or mark a length-stopped answer complete.
