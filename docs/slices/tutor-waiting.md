# Tutor waiting and completion

Q2: StudyTutor shows immediate preparation status and elapsed waiting time next to Stop, above the conversation. The draft remains editable. Completion produces one concise polite status update; timer ticks are outside live regions. No automatic reading, motion, ETA or learner-progress evidence is introduced.

The request identity remains authoritative; stopping, changing the target/work, timeout and unmount retain existing cancellation guards. Reopened browser history does not announce a new completion. Reuse existing response/model routing. No backend/schema changes.

## Verification
- 191 frontend tests pass, including delayed completion, Stop then retry with late old response, timeout preserving draft, restore without a new completion announcement, and elapsed clock/cleanup tests.
- Three isolated Chromium journeys pass: selected-answer feedback and notebook conversations at 390/1280px, including keyboard Stop, elapsed waiting and retry with preserved draft/target.
- Lint/types and production build pass; existing bundle-size/spectrogram warnings remain. Backend unchanged; prior 421-test baseline remains applicable (not rerun for this UI-only delta).
- Required independent code/pedagogy review: no blockers or majors. Manual VoiceOver remains unverified; DOM live-region tests are not a screen-reader certification.

Main streaming lesson, question help and standalone playground remain separate surfaces for subsequent reconciliation. No new prompt or model-quality claim; earlier local-model limitations remain open.
