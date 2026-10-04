# Comparison exercise recovery

2026-10-04. Browser reproduction confirmed that changing away from Audio to animation erased the selected experiment and prediction. The prediction is a select choice, not typed text.

GuidedExperiments now accepts controlled state from the lesson checkpoint, retaining its existing standalone fallback. Optional versioned state contains experiment ID, prediction, hint and revealed-comparison flag. Existing checkpoints remain valid. Lesson switches preserve it; Restart clears prediction/hint/reveal for that experiment, while Stop clears the selection too. Results still use the existing fixed synthetic calculations and are not grades or live audio measurements.

Evidence: pre-change failing browser journey, then two desktop/narrow recovery/reload/keyboard-Restart journeys pass; narrow result inspected visually. Existing 71 visualizer tests and five new checkpoint validation tests pass; lint/types/build pass. Sanitized comparison and lesson regression journeys pass. Independent read-only review found no blockers/majors, without rerunning tests. No audio, model, kernel or mastery changes. Known canvas/worker/chunk warnings remain.

Remaining C3 gaps: dedicated audio reselection state after reload, active-tone restart context, MilkDrop selection/discard, broader contextual lesson sources and owner comprehension. Comparison content changes must reconcile its checkpoint version rather than silently assuming an old reveal means the new example was explored. Broader C4/C5 work remains queued.
