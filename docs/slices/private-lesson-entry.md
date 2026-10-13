# Private lesson entry

## Problem and bounded change
After activating one private lesson, the receipt sent the learner to generic Home, potentially retaining an unrelated topic. The receipt now links to that exact lesson's selection screen. Start and existing-session replacement remain separate explicit decisions. Multi-lesson activations retain the existing chooser. No kernel, scheduling, grading, event, sensory or evidence semantics changed.

## Acceptance
- New sandbox-only saved-answer fixture; real browser forms and HTTP/storage create the draft, activate it, reload the receipt, follow its direct link, start the selected session, and reload it. No route mocks in this journey. Fixture path cannot redirect or use a custom database. Synthetic material only; finally ends session.
- Three browser tests pass: real journey plus mocked recovery journeys at390/1280. Keyboard, responsive overflow, axe, dark/enlarged text covered by recovery journeys. Receipt and lesson screenshots visually inspected. These are not human usability certification.
- Nine real activation API tests pass, including separate abstention submission: rubric feedback, score0, replay preserves attempt ID and exactly one attempt, no task-review qualification or model call.
- Twelve component tests pass, including single-lesson URL and multi-lesson fallback; lint, types, Ruff and production build pass. Existing bundle-size warning remains.
- Bounded code and pedagogy reviews: no blockers/majors. Prior full suites reused for unchanged implementation.

## Next reproduced gap
Session teaching still presents Start explanation and calls the tutor instead of directly displaying the private lesson's saved explanation/worked example. The saved text lives in LearningObject.examples; the representations catalogue returns kinds, not this authored reading. Implement an owned, versioned reading path before claiming complete answer-to-learning reuse. Keep source provenance and authored text distinct from factual verification; do not infer teaching quality or assessment review. This needs a separate bounded API/UI contract, not hidden changes to generation or the learning kernel.

Actual substantive answer grading and complete browser explanation→answer submission remain unverified here. The abstention case only tests honest absence-of-answer feedback. Live learner content untouched.
