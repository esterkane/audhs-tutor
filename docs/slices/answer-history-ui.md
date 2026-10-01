# Saved-answer browsing

Learners can reopen saved tutor replies from More tools → Saved answers or from a saved reply link. History supports surface filters and cursor pagination; detail shows the original request, response and supplied code/output. Reopening makes no tutor generation call and emits no learning evidence. Listening remains opt-in. Historical source references open the current corpus copy with an explicit caveat. No claim of correctness, freshness or mastery is made.

Status: implemented and verified. Six focused component tests pass (round trip with retained filter, retry/pagination/filter reset, empty state, 404/503, historical conversation and source qualifications). Full frontend suite before review fixes: 207 tests; final focused suite: 6 tests. TypeScript, ESLint and production build pass; existing bundle-size and WaveSurfer worker warning remain. Two isolated Chromium journeys pass at 1280px and 390px: keyboard opening/focus, context, code, filtered return, no horizontal overflow and no tutor/session/assessment POST. Fixtures are synthetic; no live model-quality claim.

Review fixes: independent code/pedagogy review found missing prior conversation and lost source qualifications. Both fixed and re-reviewed with no blockers/majors. Earlier browser run failed on an exact label locator despite successful navigation; switched to the observed accessible combobox role, then both journeys passed.

Search, suggested questions, continued chat, correction and freshness controls remain queued. Both repository variants remain private by owner instruction; the sanitized variant retains its public-release exclusions.
