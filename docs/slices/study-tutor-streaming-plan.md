# Study Tutor streaming: implementation boundary

2026-10-05 — implemented and verified; broader inference latency remains open.

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

The separately verified reuse-preference follow-up below retains explicit choice on re-entry without changing its default. General notebook execution, answer grading, audio behavior and the repeated-error UX investigation remain outside this transport slice.


## Delivered evidence

Ordinary explain/hint/chat now stream unfinished previews, followed by the authoritative existing reply. Structured feedback remains buffered. Stop and re-entry retain partial text, including multiple interrupted attempts. Disconnect cleanup is shielded against ASGI cancellation; no preview enters completed conversation history. Model, prompt, temperature, output bound and learning logic are unchanged.

Verification: 38 affected backend tests; 35 frontend tests; backend Ruff and mypy (199 files); frontend ESLint, TypeScript and production build. Two isolated Playwright journeys passed at 1280px and 390px, including delayed preview-before-completion, final replacement, keyboard interaction, re-entry and Stop; screenshots inspected. Independent focused review closed disconnect cleanup and partial overwrite findings with no remaining blockers or pedagogy concerns. No hosted model or live learner database used for tests.

This proves earlier display when tokens arrive, not a new real-model latency percentile. Existing local profiling still shows variable first-token delays; see local-tutor-latency.md. Physical audio, screen-reader testing and broader page complexity remain separate. Existing production bundle warnings remain. Saved-answer preference persistence is covered by the follow-up below.


## Explicit reuse choice on re-entry — 2026-10-05

Reproduced: switching away and returning reset the opt-in saved-answer reuse checkbox, even though the conversation survived. A failing regression demonstrated the lost choice. The existing per-session/target conversation record now also stores the boolean. Only literal true restores opt-in; legacy/malformed values default off. Turning it off persists too. No automatic request runs, matching rules change, approximate cache is enabled, or learning state is written. An existing storage-failure alert remains applicable; browser-local persistence is not database sync.

Verified: 35 StudyTutor tests, frontend ESLint, TypeScript and production build; two desktop/390px browser journeys exercise keyboard opt-in, target switching and preserved selection with no unsolicited requests. Screenshots reviewed; the long notebook page remains a separate usability issue. No backend changes in this follow-up. Existing warning about large build chunks remains.

Independent read-only code/pedagogy review found no actionable issue in the reuse preference change.

Broader CI on the preceding streaming commit exposed outstanding suite drift: test_db_core table inventory lacks thought_action; parking promotion still expects400 instead of the conflict contract409; ParkingLotButton exact payload assertion omits request_key; App tests lack dialog.close support in jsdom. These are not covered by the focused passing checks and are the next verification repair. Browser CI was still running when inspected.
