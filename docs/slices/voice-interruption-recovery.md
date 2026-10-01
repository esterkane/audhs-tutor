# Voice interruption recovery

Interrupt must stop queued speech immediately and retain the text already received. A server
acknowledgement precedes cleanup, so it is not permission to start another turn. The client
shows Stopping, ignores late speech/text updates and waits for both the acknowledgement and the old terminal message (including empty transcription).
Stop voice remains available. A 15-second cleanup timeout closes the socket and offers explicit
reconnection without resending, recording or playing anything automatically.

Completed save receipts are retained independently of the interrupted visible text. No new
learning events, assessment checks, mastery or audio retention are introduced. No automatic
mode/energy changes. Typed fallback remains usable after completion or reconnection.

This bounded fix is a prerequisite for durable voice recovery, not that feature: no reload
transcript/draft restoration, durable voice request ID, stream reattachment or audio replay.
Next: scope text/draft recovery by session/skill/language, then design server turn identities
before retrying voice work. Personal-recording quality/latency gate remains open.

Verification: frontend254, lint/types and production build passed; strict fake socket/microphone tests only, not live audio quality. Persistent interruption wording distinguishes partial display from a separately saved completed reply. Pedagogy re-review cleared the clarity finding; code re-review cleared the empty-transcription race; no remaining blockers or majors. Regression first reproduced late terminal text
replacing interrupted output. Tests cover queued audio suppression, acknowledgement versus
completion, next explicit turn, timeout, stale socket callbacks and retained completed receipts.

## Remaining durable voice design

1. Retain only bounded text/transcript and unsent typed draft under a session/skill/language/
   conversation identity; restore disconnected, without microphone or Player buffers. Provide
   explicit clear and storage-failure handling. Do not persist raw microphone data by default.
2. Assign a client utterance identity before microphone capture or typed submission. Carry a
   server turn identity on transcript, token, audio and terminal messages so stale messages can
   be rejected even across reconnects. Never treat an interrupt acknowledgement as completion.
3. Claim a durable request only after the transcript is final, with its exact session/context
   fingerprint. Reconnect checks terminal text status; it must not re-transcribe or regenerate
   automatically. A missing terminal remains unresolved until explicit new work is chosen.
4. Replay completed text/receipt only, never queued audio. Listening to a saved response is a
   separate learner action. Keep capture permission, generation and playback states distinct.
5. Test interruption before transcript, during inference, during playback and after terminal;
   lost delivery, duplicate submission, reconnect, stale callbacks, storage denial and actual
   persisted model/event counts. Measure personal microphone latency separately from fakes.

Code review caught empty transcription releasing a new turn while the old interrupt timer was armed. Both acknowledgement and terminal are now required in either order; the fake-timer regression confirms a following turn is not closed by the old timer.
