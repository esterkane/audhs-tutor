# Voice and reading coordination — 2026-10-03

## Behavior

Requested readings and voice conversation turns share the existing ephemeral in-tab owner.
Talk and voice-enabled Send replace a prior reading before recording/requesting an answer.
Connect, empty messages and text-only conversations do not displace readings. Incoming audio
requires an owned voice activity and cannot acquire ownership itself.

Starting a reading stops the prior voice activity: microphone and pending acquisition, queued audio
and socket are stopped. Already received transcript/answer and recovery stay available; no automatic
resume or regeneration. VoicePanel explains why it stopped. All shared Audio controls panels show
Voice activity with Stop voice activity; reading still exposes its supported Pause/Resume/Stop.
Voice Stop closes capture and connection, so it is not mislabeled as a playback-only pause.

Ownership lasts through preparation and queued playback, releasing after terminal response plus
audio drain or on stop/error/unmount. Identity-guarded release/update cannot overwrite a newer owner.
The existing `readingOwner` export names are retained for compatibility; its payload now distinguishes
reading and voice. No backend, model assignment, dependencies or persistent learning state changed.

## Verification

- Full frontend suite333/83files passed.
- Five added hook cases cover Connect/text-only/empty no displacement; queued audio through terminal
  response; pending microphone and late audio after replacement; shared stop preserving text;
  failed send/socket-error release. Existing VoicePanel test now sends an explicit request before
  simulated audio rather than treating unsolicited audio as valid.
- Isolated browser coexistence journey passed at8051/5215: real Session/VoicePanel/ReadAloud components,
  held fake synthesis, fake WebSocket and silent fake AudioContext. No real microphone/output/model.
  Connect preserves reading; voice Send replaces it; another reading closes voice and retains text;
  shared transport switches owner correctly. Sandbox session closed afterward.
- Changed-file ESLint and TypeScript check passed. Independent code and pedagogy reviews clear. Integrated full frontend333 and five browser journeys passed; lint/build verified during integration.

## Limits

One tab only. Listening clips, visualizer sound, ambient sound and test tones are not yet coordinated.
Silent visualizer analysis must remain independent in the next slice. Physical Bluetooth audibility
and owner comprehension remain open; tests do not establish either.
