# Audio lesson control recovery

2026-10-04. Reproduced in browser: selecting Harmonics and leaving the lab returned to Amplitude. AudioLessons held its own route-local state.

The visualizer now owns the lesson state and includes it as an optional field in its versioned editing checkpoint. A stable lesson identifier, bounded tone settings and hint visibility are validated before recovery. Existing records without the field retain their graph/history and use initial lesson controls. Recovery does not start or update a tone; explicit controls still update an active tone. No learning logic or model routing changes.

Evidence: failing pre-change browser reproduction; desktop and narrow route-return/reload tests pass with retained square wave, amplitude and hint; keyboard amplitude adjustment passes. Narrow screenshot inspected. 71 visualizer unit tests, lint/types and build pass. Independent read-only review found no blockers/majors (tests not rerun by reviewer). Sanitized browser regression also covers paused file return. Existing canvas-test and worker/chunk warnings remain.

Remaining: GuidedExperiments predictions/comparison state, active tone restart context, explicit file-reselection after reload, MilkDrop selection and discard controls. Live measurements are deliberately not presented as recovered/current measurements. This closes lesson step/settings/hint recovery only, not the full C3 lifecycle or owner acceptance.
