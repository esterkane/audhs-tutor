# Visualizer route recovery: implementation contract

Status: inspected and planned, runtime implementation pending. 2026-10-04.

## Concrete problem and current lifecycle

`Visualizer.tsx` owns file, input, position, view, applied preset, editor text/history, renderer selection and previous audio while a lesson tone plays. Its unmount effect aborts and stops both current and previous inputs. That cleanup must remain. `useDraftHistory.ts` is component state; the library stores only explicitly saved applied presets, not unfinished editor text. `AudioLessons.tsx` also owns lesson step and tone settings. Retaining only the route query or applied preset cannot meet the design requirement.

The intended user flow is leave the lab for a lesson or preferences, return to the same work, inspect a paused state, then explicitly resume. There must be no background playback or new inference, learning evidence or session creation.

## State ownership decision for implementation

Use one app-lifetime workspace checkpoint, separate from the durable named-preset library. Store serializable editing state and an optional in-memory File reference, never a live AudioInput, AudioContext, stream, abort controller or audio lease. Do not keep the hidden route mounted: its animation loop, lesson state and audio effects were designed for a visible page.

Capture the exact input position before stopping resources. Keep the current and previous source descriptors separately, so leaving during a test-tone lesson does not erase the original file return point. Source descriptors are demo, local file or test tone; tone descriptors contain validated settings. Returning mounts stopped resources. Resume opens the input muted, seeks/clamps position, reapplies a valid repeat range, and starts only after the explicit action. Sound requires a fresh opt-in. A cancelled or superseded resume must dispose its newly opened resources even if decode completes later.

An in-memory File is retained only until tab reload/close or explicit workspace discard. Do not serialize audio or inferred file paths into localStorage. A reload may recover bounded JSON work but must require file reselection; display that distinction plainly. Reselection must not silently associate a different file with the old position. Storage denial must keep the current in-memory draft and offer export without claiming it is saved.

## Bounded implementation sequence

1. **Editing checkpoint.** Versioned, validated draft schema: raw text (including invalid unfinished JSON), applied graph separately, bounded undo/redo, selected view/renderer/preset identity. Preserve named-library Save semantics; expose temporary recovery vs explicit saved preset. Add app-lifetime memory and bounded browser draft recovery. Do not claim media recovery at this step.
2. **Paused media checkpoint.** Add source/current-and-previous descriptors and memory-only File, capture position before cleanup. Explicit Resume recreates resources under generation and abort guards. Reset/discard clears matching checkpoints without deleting the named preset collection. Pending file-open cancellation and end-of-file semantics must be tested before enabling this path.
3. **Learning-panel checkpoint.** Lift or serialize lesson selection/settings and unfinished comparisons deliberately; distinguish historical measurements from current live measurements. Restore explanatory context without silently starting a test tone. Then verify the full context-tool round trip with existing lesson and coding origins.

Expected files: features/visualizer/workspaceCheckpoint.ts and tests (new), useDraftHistory.ts, AudioLessons.tsx, routes/Visualizer.tsx and tests, app-level ownership only if needed, dedicated browser journey, slice/handoff docs. Avoid moving unrelated shell or learning-kernel code.

## Required evidence

- Unsaved valid and invalid JSON survives route return; Undo/Redo still refers to the restored history. Applied graph never becomes invalid editor text.
- File at a known nonzero position: leave while playing, verify sound stops and resource disposal, return paused, Resume at that position; no stale audio-ownership registration.
- Leave during decode/resume; resolve old operation after return; no playback or overwrite. Repeat with rapid source switches.
- Leave during a tone lesson, return to that lesson, then restore original file and position without autoplay.
- Reload with no memory File: honest reselection state; no fabricated successful resume. Denied/full/corrupt/unknown-version storage leaves active work intact.
- Back/Forward, preferences detour, keyboard Resume/return, narrow screens and reduced motion. Source measurements may update independently of animation only during explicit running state.
- Existing renderer fallback, Save/library migration, view continuity, global audio ownership and source disposal tests remain green. No session or mastery writes.

Do not mark C3 complete until these integrated gates pass. Persistent tutor remains a separate C5 slice. This is a frontend lifecycle decision, not a new backend, model provider or learning-state architecture.

## Reproduction evidence

A disposable browser probe opened Create → Advanced JSON, entered unfinished text, navigated to the playground and returned: the text was lost and the demo remained stopped. The probe passed as a characterization of the current defect, not a recovery acceptance test; temporary test removed after inspection. Initial probe omitted expanding the Advanced disclosure, was stopped, then corrected. No runtime code changed in this planning slice.
