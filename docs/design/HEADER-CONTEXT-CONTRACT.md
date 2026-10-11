# Compact header and learning context contract

Authority: Complete Design System PDF pp6/9/11; follows the implemented
five-destination shell. Inspection:2026-10-11. This is the next incomplete
layout phase, not a new learning feature.

## Current problem and inspected ownership

The header still uses multiple rows for brand/search, tutor entry, audio,
saved thoughts, area browsing and mode/energy. At narrow widths it consumes
substantial space before the current task. Navigation alone did not resolve
this. The PDF calls for a48px header, page-level tutor entry and a Learn
ContextBar showing goal/concept/step with Pause and Focus.

Relevant implementation:
- `app/App.tsx`: header placement, main landmark, route focus, tutor entry root.
- `components/QuickNavigation.tsx`: native modal and return-focus ownership.
- `components/ParkingLotButton.tsx`: Radix dialog, captured context and durable
  unsent draft. Must not be remounted on breakpoint or menu toggling.
- `features/audio/AudioControls.tsx`: compact mode renders current playback
  activity outside its settings disclosure. Settings include output test
  lifecycle; unmount cleans it up. Keep a single visible global control owner.
- `features/programs/LearningCompanion.tsx`: launcher captures main content and
  retains the originating path/context; entry is a portal. Move its existing
  target, do not create a second companion or replace captured context.
- `features/areas/BrowseArea.tsx`: browsing is separate from learning selection.
- `routes/Session.tsx`: session controls already precede SessionBody. The body
  has concept/activity/plan data; the global shell must not infer a different
  session or duplicate phase transitions.
- `features/session/SessionControls.tsx`: Pause navigates Home without grading;
  End/Change topic use existing server lifecycle. Preserve these handlers.

## Smallest coherent implementation

1. Move the existing tutor portal target to a page-level action row beside the
   content heading area. Preserve the single LearningCompanion instance and
   launcher focus, active capture and saved chat across resizing/navigation.
2. Build a compact global header using the existing brand, search, audio and
   saved-thought controls. Responsive presentation can shorten visible labels
   with icons, but retains accessible names and44px targets. No new library.
   Audio settings can disclose; active playback status and Stop remain reachable
   without first opening settings. Do not hide a playing owner's Stop control
   merely to force the header to48px.
3. Place browsing and mode/energy information in secondary navigation/context
   presentation, retaining existing browsing semantics and learner choices.
   Avoid a new mutable goal selector in the shell. Do not put active playback
   or save-dialog triggers inside a modal that prevents their own dialogs.
4. Consolidate the lesson orientation and existing SessionControls into one
   ContextBar. Reuse authoritative SessionOut/plan/skill fields; expose missing
   goal context honestly. Keep one Pause and End path, assessment drafts and
   optional confidence unchanged. This requires inspecting goal provenance
   before choosing labels, not copying current global preferences as history.
5. Add temporary Focus presentation with visible Leave focus and Escape.
   Hide header/navigation without unmounting their stateful owners. Reset on
   leaving the learning route, preserve text/cursor/session position, and give
   nested dialogs/editors first handling of Escape. Audio already playing must
   retain a visible stop path. No preference write or automatic adaptation.

## Verification before publication

Baseline: current shell mobile screenshots show the multirow header; the new
navigation passed601 unit and28 affected browser checks. Those results do not
verify this unimplemented phase.

Run desktop/narrow/large-text/light/dark/reduced-motion journeys. Measure the
idle header against48px, permit documented content-driven expansion where
needed for active playback/accessibility instead of clipping controls. Verify:
- every action's label and keyboard access, no overlapping targets;
- saved-thought draft and captured original context survive layout changes;
- tutor chat/capture stays attached to its source, with return focus;
- audio volume/rate/output/Stop remain available during playback and Focus;
- Escape closes the innermost modal first, then Focus when appropriate;
- lesson Pause/End/Change topic do not submit, grade or alter optional confidence;
- session reload, Back/Forward and failure recovery retain the existing contract.

Inspect the rendered result and obtain bounded code/pedagogy review. Retain
human comprehension and screen-reader checks as separate open gates. No model
calls, new providers, competency changes or new state stores are justified by
this layout phase. Publish both variants only after the coherent slice passes.

## First ownership-preserving change verified

The existing companion launcher now appears in the page action area above
main, outside the captured content region. Its portal target and companion
instance remain mounted through navigation/resizing. The page action/main
wrapper occupies the original workspace grid column beside the tutor. Header
audio and saved-thought owners are untouched.

Six companion browser journeys pass: desktop/narrow context and draft return,
reload, failed storage, exact pending-request recovery, invalid checkpoint and
resize with one conversation. Added assertions cover keyboard launcher entry
and absence of launcher text from captured material. ESLint and production
build pass; desktop rendering inspected; bounded code review found no issues.

This places the page-level tutor entry but does not complete the48px header or
ContextBar. The action remains above the route title rather than sharing a
common title component; title consolidation can follow without duplicating
existing route headings. Next: compact global controls with visible playback
Stop, followed by authoritative lesson context and Focus.
