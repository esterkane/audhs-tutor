# LT1 foundation: bounded opening-question context

Problem reproduced2026-10-15: by the fifth Ask turn, the opening question is absent from the model packet. Recent history remains limited to three exchanges. This can lose the learner's practical starting point before a full conversation brief exists.

Preserve the exact owned opening question as historical learner input, never a verified fact or an immutable current goal. Fetch the canonical root through the stored conversation identity with learner/surface/area checks. Do not traverse an unbounded ancestry or replay its answer/source passages. If unavailable, disclose that limitation instead of reconstructing it from model output. Escape its text and clearly state that the current question takes precedence.

Only add the opening-question block when it falls outside recent history. Record its identity/text hash and the omitted-history state with the saved answer, and show an optional context disclosure. A current first question needs no extra prompt block. Existing selected-source behavior remains explicit per reply; past citations do not become current evidence. No model summarization, new tables, mastery evidence, routing change or automatic Socratic mode.

This is not the complete LT1 brief: intervening facts, assumptions and unresolved questions still need a reviewed retention design. The interface must say that older intervening exchanges are omitted. Saved-answer identity includes actual prompt packets. Keep receipt replay exact; root deletion must not silently regenerate an already completed request. Legacy/foreign/missing roots must not leak another learner's material.

## Implementation checkpoint — 2026-10-15

Uncommitted foundation implemented. Regression initially failed because conversation identity is the opening turn ID, distinct from the saved answer ID. Canonical root lookup now uses owned Ask turn identity; retained context records the actual root answer ID when fetched. A first-turn context records only its turn ID rather than mislabeling it as an answer ID.

Current verification: 12 backend tests pass (opening retention, independent new topic, unavailable root disclosure, exact replay, existing Ask tests); two context-disclosure component tests pass; frontend TypeScript build checking and targeted ESLint pass. Backend changed-file Ruff passed before the final added test. `git diff --check` passes. No paid inference used.

Still required before publication: ownership/area and escaped-input edge coverage, code/pedagogy review, real browser flow with keyboard and narrow layout, relevant broader provenance/reuse checks. The UI and prompt changes are not yet accepted as a complete LT1 implementation. Instructional-design quality directions are documented separately and must ship with the verified slice, not as an independent runtime claim.


### Extended checks

34 backend tests pass across opening-context boundaries, Ask requests and exact saved-answer reuse. Explicit tests cover foreign owner, different area, non-Ask surface, deleted root, escaped markup, current-question priority and replay after root deletion. Both bounded source reviewers found no blockers/majors; they did not independently execute the tests. Production build and targeted mypy pass; the existing large-chunk build warning remains. Browser fixtures initially omitted required `request_text`; corrected before rerun. Browser evidence remains pending until the corrected run and screenshots are inspected.


## Final bounded acceptance

44 affected backend tests pass (opening boundaries, Ask, reuse and source lineage); the source prompt-version assertion was updated to the intentional new identity. Two component tests and two Chromium journeys pass at390/1280px. Browser tests use saved-answer HTTP fixtures, not generated-model quality evidence; backend tests separately exercise real request/storage logic with a fake local provider. Keyboard Enter/Space toggling, reload, new-topic clearing and no horizontal overflow pass. Both screenshots inspected: text wraps and focus is visible. Targeted Ruff/ESLint/mypy, TypeScript, production build and diff whitespace checks pass. Existing bundle-size warning remains. No hosted inference or live learner DB modification.

This closes only the opening-context foundation. Full LT1 factual/assumption/source brief, guided-mode implementation, real-model multi-turn quality, human comprehension and assistive-technology acceptance remain open. Planning directions from the instructional-design report are included without runtime efficacy claims.
