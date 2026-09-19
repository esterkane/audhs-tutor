# Kokoro-82M persistent TTS server (:8880)
Run natively on the Mac for Metal acceleration (Docker = CPU only). Options:
1. `uvx --from kokoro-fastapi kokoro-fastapi --port 8880` (OpenAI-compatible /v1/audio/speech), or
2. `pip install kokoro soundfile` + `backend/app/voice/kokoro_server.py` (FastAPI wrapper, MLX/MPS).
Keep it running; a cold CLI start costs ~6 s per utterance, a warm server ~100–300 ms to first audio.
Verify: `curl -s localhost:8880/v1/audio/speech -d '{"input":"hallo","voice":"af_heart"}' -o /tmp/t.wav`
