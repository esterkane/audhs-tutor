# 0011 — Local voice runtime and TTS routing
Date: 2026-09-21
Status: Accepted

## Context
Owner requested resolution of the dependency decisions in IMPROVEMENT-PLAN and execution of the local setup and commit plan.

## Decision
STT uses the registry MLX Whisper adapter and optional stt dependency group. VAD uses the registered Silero ONNX artifact with the existing energy fallback explicitly reported. TTS uses TaskClass.TTS and a persistent Kokoro OpenAI-compatible server bound to 127.0.0.1:8880; it is an optional voice service, not a general-inference MLX provider. General inference stays on Ollama. Keep per-call accounting. Never auto-enable microphone capture, hosted realtime, or voice activation. Unsupported TTS languages, including German for Kokoro v1, remain visibly unavailable. Stage 5 remains open until >=20 own recordings have a real measured result.

## Consequences (positive / negative / follow-ups)
Amends the voice-runtime clause of ADR-0001; its other routing decisions remain in force. Benefits: matches the implemented adapters and separates service startup from learner activation. Costs: another optional service and CPU latency to measure. Alternatives: MLX TTS adapter or another TTS model; defer until benchmark/language needs justify it.

## Alternatives considered
See consequences above; retain the implemented fallback until each replacement passes acceptance checks.

## Evidence / sources
https://github.com/remsky/Kokoro-FastAPI
Project: docs/IMPROVEMENT-PLAN.md; docs/HANDOFF.md; relevant slice docs and implementation.
