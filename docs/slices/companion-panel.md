# C5 persistent tutor panel

## Problem and implementation

The retained companion lived below each page, requiring learners to leave the visible material to find help. It now has a global header entry, a nonmodal desktop side panel and a full-height native modal sheet below 64rem. The same dialog and conversation remain mounted during breakpoint changes; explicit closing still unmounts request/media children for existing cleanup and recovery. The narrow origin link closes the sheet and reveals the destination; desktop browsing retains the panel.

Existing capture/apply/previous-context checkpoints, session identity, provider routing and learning logic are unchanged. No dependencies or backend changes. The panel uses existing surface/control tokens, with one semantic 24rem tutor-width token; the uploaded reference does not prescribe this dimension. Native modal containment supplies keyboard isolation; Close remains sticky at the top. No sound or inference starts on opening.

## Verification

Baseline desktop journey passed before edits. Inspected desktop and narrow rendered screenshots. Relevant tutor/shell component tests: 33. Browser coverage: companion recovery and Library journeys, including 390/1280 flows, 320px panel overflow, 200% text size, keyboard close/reopen, modal containment, Escape, origin return, draft/apply/previous context, denied/invalid storage, exact pending-request retry and one connected conversation across resize. The resize test waits for the actual modal state before Escape; viewport mutation alone does not synchronously dispatch matchMedia changes.

Read-only state review found no blocker/major. Pedagogy review identified the hidden mobile origin destination; fixed and directly covered. Final sanitized rerun passed all 10 browser journeys and 33 component tests; full frontend lint, type checking and production build passed. Both reviews cleared the final delta.

## Remaining scope

Human comprehension, VoiceOver and real microphone/Bluetooth acceptance remain open. StudyTutor remains whole-response, separate from the lesson streaming tutor; these tests do not establish unified cross-surface conversations. The current tutor contains substantial explanatory/configuration copy: assess progressive disclosure in a subsequent bounded slice, preserving safety and context information. Existing production bundle-size and spectrogram worker externalization warnings are unchanged. C6 resume-first Home/audio/capture remains next in the workspace sequence after C5 acceptance.
