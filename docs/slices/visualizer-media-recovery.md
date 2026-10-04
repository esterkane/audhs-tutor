# Visualizer paused file recovery

2026-10-04. A selected local File, position, repeat range and resume eligibility now survive route changes in tab memory. The checkpoint holds no live input or audio context and is never serialized/uploaded. Route cleanup captures position before abort/stop, then releases both current and previous resources. Reentry is stopped, with sound unchecked. Resume recreates input and restores position; Stop resets the next playback to the beginning. Controls requiring a live input stay disabled until Resume.

Review found a tone-detour edge case: a recovered file has no input yet, so a tone lesson could lose its previous position. Previous audio now retains fallback position and resume eligibility; both direct return and leaving during the tone retain them. Late input completion is disposed and cannot replace a newer restored input.

Evidence: 64 visualizer tests, lint/types/build pass. Original two real-WAV browser cases verify four-second position, paused reentry, keyboard Resume, no narrow overflow and file release on reload. Five sanitized browser cases pass including draft/storage recovery regression. Narrow screenshot inspected. Existing canvas-test and worker/chunk warnings remain. No learning writes, providers or libraries changed.

Remaining: audio files/positions are intentionally unavailable after reload or tab close; use Open audio to reselect, and no matching file is inferred. Reload currently returns to the silent demo rather than a dedicated reselection view. Tone settings, lesson steps and measurements are not recovered; returning from a tone detour restores its previous file rather than the tone. MilkDrop selection, explicit discard UI, integrated repeat-range recovery browser verification and owner comprehension remain open. Full lifecycle/C3 is not complete. Next: lesson-panel recovery and explicit source/reselection states under the existing plan.

Follow-up independent read-only review confirmed the tone-detour fix and found no remaining majors in this delta; reviewer did not rerun tests.
