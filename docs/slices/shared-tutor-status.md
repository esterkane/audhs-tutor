# Shared tutor response status

Extend quiet elapsed waiting and completion status from StudyTutor to streamed lesson explanations, assessment help and the standalone coding playground. Share one status component; keep tokens and timer ticks out of live announcements. Distinguish complete, partial, stopped and failed replies; no ETA, audio autoplay, confidence gate or mastery evidence.

The playground Stop previously only aborted fetch and waited for it to settle. Reproduce with a transport that does not settle on abort. Make Stop and timeout terminal immediately; guard response, error and finalization by request identity. Preserve current question/code/history, retain existing earlier-code labels, and clean up on workspace change/unmount. Streaming keeps its existing tested interruption logic with a per-request monotonic start time.

## Verification
- 196 frontend tests, lint/types and production build pass. Existing bundle-size/spectrogram worker warnings remain. Backend unchanged (prior421-test baseline, latest prior public CI fully green).
- Seven relevant browser cases pass across the final reruns: lesson explanation, real local Python playground, two desktop/narrow Stop/retry journeys, session clarity and two desktop/narrow notebook tutor conversations.
- Initial playground regression failed because Stop left Send disabled with a non-settling transport; now passes. Timeout also ends waiting immediately and late callbacks cannot replace the current reply. Hook test verifies token arrivals do not reset elapsed time.
- Browser surfaced a pre-existing deferred composer-focus race. Completion now checks request generation and whether focus remains on the sender (or body after the sender is disabled), preserving another focused control. A unit regression plus desktop/narrow Socratic focus journeys pass. Stop/work edits/unmount invalidate old focus callbacks.
- Independent code/pedagogy review and focus follow-up review: no blockers/majors. Live-region DOM assertions do not certify manual VoiceOver behavior.

No backend API, dependency, prompt or routing change. Source-view consistency and earlier model-quality limitations remain open; this does not close all Q2 or the saved-answer-library queue.
