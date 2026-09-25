# Visualizer block controls and local explanations

Continue the tutor-integrated visualizer with direct controls for visual style/color and each existing block's parameters, plus three explicit-load examples. Controls edit the same JSON draft; Apply remains explicit and saved presets are preserved.
Explain buttons show deterministic descriptions of the selected block, its dependency and limits. Unapplied drafts never show old visual output as their own. Example instructions remain explicit and repeatable.
No new schema, API, model, database, event or mastery changes. All calculations remain in the browser; no audio or live features leave it. Existing mode/energy/sensory behavior is unchanged.
Keyboard-native labeled controls; detailed block editing collapsed initially. Test draft/apply separation, invalid JSON recovery, parameter limits and explanation accuracy, plus browser/axe checks and required reviews.

Verification (2026-09-24): 77 frontend tests pass; backend/frontend lint and types pass. Isolated Chromium journey passes feature selection, explanation before/after apply, numeric editing, saved-preset persistence and local audio lifecycle without upload/mutation requests. Screenshot inspected. Code and pedagogy re-reviews cleared blockers/majors after numeric editing, live-announcement and example-comparison fixes. Bars honor scale with a regression test. No backend behavior or API schema changed.
