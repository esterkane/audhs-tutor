# Output sound test ownership

The explicit half-second sound test participates in the existing in-tab audio owner. It replaces
another activity and exposes a stop-only Sound test entry in shared controls. Finishing, failure,
replacement and unmount release ownership and close the context. Each invocation owns its cleanup;
an old resume resolution/rejection or ended callback cannot revive audio, close a newer test or
clear a newer activity. Test controls remain disabled when muted or volume is zero.

The shared control contract now also supports stop-only ambient and visualizer monitoring entries,
with distinct labels. Pause/resume controls remain limited to readings and listening clips; voice,
noise, tests and visualizer sound do not acquire misleading reading controls.

Verification: six component tests cover output preference sharing, unmount during resume, replacement,
old resume rejection, cross-control Stop, old ended events, completion and current failure. Together
integration adds four tests and a silent browser journey switching ambient noise and the sound test
through the app header. Independent code/pedagogy reviews clear. All audio is simulated in these tests;
physical Bluetooth output, macOS device selection and audibility remain user-device checks.

CI follow-up: the preceding Home revision exposed a listening-control test race on Linux: the playing
notice appears before the pending play promise clears. The test now waits for Replay to become ready
before pausing through shared controls. ListeningPanel's eight tests pass; this changes only test
synchronization, not playback behavior. The next remote run must confirm the CI result.
