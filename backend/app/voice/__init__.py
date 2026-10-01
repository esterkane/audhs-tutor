"""Voice (P9): setup lifecycle, VAD, STT/TTS adapters behind the registry, the WebSocket loop.
MLX Whisper for STT and a Kokoro-82M persistent server for TTS (CLAUDE.md / ADR-0001); the donor's
faster-whisper + Piper stack is deliberately not adopted. Nothing here downloads or activates
anything by itself: install, verify, test and activate are separate, learner-initiated steps."""
