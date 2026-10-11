# Ci Gates

Implementation details are documented by the source code and regression tests. Private execution history is retained locally.

## 2026-10-11 — Conservative documentation reuse

Runtime gates may be reused only for a push changing README.md or docs/**/*.md,
when the latest CI push run for the exact pre-push commit completed successfully.
Pull requests, code/config changes, empty diffs, missing evidence and API/git errors
run all gates. Rename detection is disabled so moving code into docs cannot hide a
runtime deletion. Running validation is no longer cancelled by a subsequent push.
The public repository always checks its publication contents before scope selection.

Verification:15 classifier/evidence/failure-path tests, Ruff and bounded code review
passed. No application, learning or UI behavior changed; prior passing browser suite
38129974426 is unchanged-code evidence. Workflow execution on GitHub remains to
verify after publication; no spending reduction has yet been measured.
