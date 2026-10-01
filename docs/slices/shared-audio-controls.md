# Shared audio controls

User story: hear local explanations through the selected Mac output and control volume/speed beside every app playback surface.
Shared browser-local settings apply without model calls or learner events. No autoplay or microphone permission is added; sensory opt-ins remain independent.
Accessible labeled volume/speed/mute controls and an explicit short test tone distinguish output troubleshooting from voice-service readiness.
Voice PCM speed is latched per response to preserve queued timing; it changes pitch. File speed is live; scientific test signals and ambient audio keep their original speed.
Bluetooth hardware audibility requires owner verification; the browser uses the system output and does not claim to identify headphones.

Verification: 173 frontend tests pass, including output propagation, queue timing across delayed chunks, cleanup during pending resume and storage denial. Isolated Chromium journey passes for route/reload persistence, narrow layout, keyboard mute and test-tone lifecycle. Production build and frontend lint pass. Independent code review: one major (speed changing between delayed chunks of one response) fixed and regression-tested; re-review has no blockers or majors.

No hardware audibility claim: physical Bluetooth output and owner comprehension remain to be checked. Local voice readiness reported TTS available but conversational voice deactivated; this slice does not silently activate microphone conversation. Read-aloud remains usable without activation. Global mute does not stop generation; each surface keeps its Stop action.
