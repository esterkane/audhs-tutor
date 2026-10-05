# Study Tutor streaming: implementation boundary

2026-10-05 — next performance slice, not implemented.

## Concrete problem

Session explanations already render SSE tokens. Study Tutor uses `askTutor()` against the buffered `/api/playground/tutor` endpoint. `playground.respond()` waits for a complete model answer (up to900 output tokens), then performs disclosure/check rendering and saves the result; `StudyTutor.execute()` cannot display new text until this whole response arrives. Fast first-token inference therefore does not currently benefit this surface. This is code-path evidence, not a new timed browser measurement.

Existing answer history is intentionally bounded, source-checked, and labelled unverified. Removing it indiscriminately is not justified by the measured latency. Exact saved-answer reuse is already opt-in for the workspace. Do not introduce a second approximate-answer cache or silently enable reuse.

## Smallest coherent implementation

One vertical slice: stream only ordinary Study Tutor explanation/hint/chat, preserving the existing completed-reply contract. Keep answer checking, starter templates and deterministic bin checking on their existing buffered paths. No model, temperature, token limit, prompt, retrieval, learning policy or paid-provider change.

Likely files: `backend/app/api/playground.py`, `backend/app/orchestrator/playground.py`, a bounded model gateway streaming-completion helper if needed, `frontend/src/features/playground/api.ts`, `frontend/src/features/programs/StudyTutor.tsx`, focused backend/frontend tests and an isolated browser journey. Reuse existing SSE framing and request recovery; do not duplicate the tutor orchestrator.

### Backend contract

- Add an SSE workspace endpoint whose body and idempotency fingerprint match the buffered request. Validate ownership/origin before new work. An already completed identity replays the saved final reply without model inference.
- Provide ordinary text tokens during generation. Preserve complete()'s temperature0.2 explicitly; gateway.stream() otherwise defaults0.3. Preserve its900-token bound and routing task.
- Stream previews are unfinished, unverified and not saved answers. Final disclosure, source checks, arithmetic/bin caveats, stale-output warnings and answer saving remain authoritative. The done event contains the existing PlaygroundReply; it may differ from raw preview text.
- Structured checks and starter plans must never expose partially parsed fields as checked feedback. Keep those on the original endpoint.
- Preserve final model usage, cancellation/partial accounting and the original durable request identity. Do not invent safe retry from a disconnected stream. Existing recovery can reopen a completed reply via the original buffered endpoint.
- Bound any queue, close generators/tasks on disconnect, and await cleanup while the request database session remains usable. No orphaned background generation on Stop.

### Frontend contract

- Show first tokens immediately in a clearly labelled unfinished preview with Stop reachable. Announce state transitions, not every token. Keep the previous completed reply and unsent message available.
- Commit reply/history/mode/save state only from the authoritative done event. Do not treat preview text as graded, source-verified or saved, or send it as completed history.
- Preserve partial text on Stop/error/timeout. Scope every callback to the request and target snapshot so changed code, topic or unmount cannot receive stale output. New explicit requests must not silently erase retained partial work.
- Keep the same request key for explicit recovery, with no automatic resend. Saved-reply replay must show its existing provenance/reuse disclosure.
- Avoid token-by-token storage writes and audio autoplay. Retain current controls and design tokens.

## Verification before publication

Backend: token precedes held completion; final reply preserves text/disclosures/save identity; replay calls model once; errors before/after text; disconnect/cancel accounting; source/ownership isolation; structured routes unchanged; temperature/output limit unchanged.

Frontend: preview arrives before final reply, Stop retains text and draft, late output ignored after target change/unmount, final text replaces preview correctly, recovery uses original identity, no duplicate history/learning evidence, storage failures visible, buffer-only intents still checked after completion.

Browser: real disposable sandbox with delayed token/done fixture, desktop and390px, keyboard Stop/recovery, screenshot review, double-click and mid-response navigation. No owner database or hosted model used. Separate fixture UI evidence from real-model latency and teaching quality.

Run affected backend/frontend tests, lint/types/build and independent code/pedagogy review. Record time to first visible text and full completion separately. Use unchanged-source quality regression checks; any generated-content difference is not automatically an improvement.

## Follow-up, not bundled

Saved-answer reuse preference currently lives only in component state and is not included in the saved conversation. Investigate retaining an explicit choice on re-entry as a separate bounded UX change; do not change the default silently. General notebook execution, answer grading, audio behavior and the repeated-error UX investigation remain outside this transport slice.
