# Durable voice terminal results

Identified voice responses claim the existing private request ledger before LLM/TTS work.
The claim binds learner/session, transcript, skill, language, conversation and text-only mode.
Terminal text, original turn/save receipt and interruption status persist before final delivery.
A repeated matching request returns text only with replay metadata; no audio, inference, events
or checkpoint updates are repeated. Changed payload conflicts; unresolved claims never rerun.

GET /api/voice/requests/{UUID}?session_id=… reads an owned voice-namespaced request and returns
not_found, unresolved, completed or partial. It does not create a claim, transcribe, infer or play
anything. A failed terminal save leaves the earlier claim unresolved and retains delivered tokens.
No migration: existing request-ledger backup/export/wipe handling applies. No mode/energy change,
paid-provider routing or automatic audio retention.

This backend foundation does not yet offer the browser recovery action or persist the pending
UUID across reload. Speech transcription occurs before the LLM/TTS claim: replaying raw capture
is not an STT deduplication guarantee. The planned client must check the read-only result endpoint,
not resend recorded audio. Provider-resistant connection teardown remains separate.

Acceptance: complete/partial results replay without new provider/TTS/model/event/answer writes;
changed payload rejected; read-only owner-scoped missing/unresolved/partial lookup; failed terminal
save leaves uncertainty and cannot regenerate. Backend 587 and frontend 262 tests passed;
generated API types, lint/types and production build passed. Fakes only; personal voice benchmark
stays open. Existing production-build chunk-size warning remains.

Review fixes: code review found an interrupt race while awaiting the durable claim. Interrupt
initialization now precedes task scheduling; interruption after admission persists a partial result
without model or speech work. A gated real-ledger regression covers that sequence. Code re-review
and pedagogy review have no remaining blockers/majors. Replayed terminal messages explicitly carry
recovery_status; browser presentation and pending-request persistence are the next slice.
