# Keep calculation checks while explaining results

The run → explain → return journey was blocked: every draft update cleared the checked flag, so writing an explanation after a successful run required needless execution again. Cell navigation also discarded the output used for returning results.

The workspace now retains the successful full-run result separately from the currently displayed cell output. Prediction/explanation edits and cell navigation preserve it; code edits, starting another run and stopping invalidate it. Return uses the validated full-run output snapshot. A visible note says calculation checks passed for unchanged code and do not grade the explanation. Results remain page-local; reopening still requires a new run, avoiding unsupported claims about persisted execution.

Regression coverage follows full run → explanation → feedback → cell navigation → return, and asserts that editing code disables return. Verification: all 407 frontend tests, lint/types/build and the isolated browser starter→run→explain→feedback→navigate→return journey passed. Independent code review found no blockers or majors; pedagogy review identified the original blocker. No model route, API, database or mastery change.
