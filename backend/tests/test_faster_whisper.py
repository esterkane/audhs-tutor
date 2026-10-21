import sys
from types import SimpleNamespace

import numpy as np
import pytest

from app.core.config import Settings
from app.knowledge.ingest.faster_whisper import FasterWhisperTranscriber
from app.knowledge.ingest.media import SttSupportMissing, load_cached, save_cached
from app.voice.setup import stt_for


def test_missing_snapshot_never_imports_or_downloads(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "faster_whisper", None)
    with pytest.raises(SttSupportMissing, match="missing or incomplete"):
        FasterWhisperTranscriber(str(tmp_path), registry_id="ct2").transcribe(
            tmp_path / "audio.wav"
        )


def test_local_loading_timestamps_language_and_reuse(tmp_path, monkeypatch):
    for name in ("config.json", "model.bin", "tokenizer.json"):
        (tmp_path / name).touch()
    monkeypatch.setattr(
        "app.knowledge.ingest.faster_whisper.read_wav_mono16k", lambda path: (np.array([0.1]), 2)
    )
    calls = []

    class Model:
        def __init__(self, path, **kwargs):
            calls.append((path, kwargs))

        def transcribe(self, path, **kwargs):
            assert kwargs["language"] == "de"
            return iter([SimpleNamespace(start=0.5, end=1.2, text=" Hallo ")]), SimpleNamespace(
                language="de", duration=2
            )

    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=Model))
    transcriber = FasterWhisperTranscriber(
        str(tmp_path), registry_id="ct2", model="converted-turbo"
    )
    result = transcriber.transcribe(tmp_path / "audio.wav", language="de")
    transcriber.transcribe(tmp_path / "audio.wav", language="de")
    assert len(calls) == 1 and calls[0][1]["local_files_only"] is True
    assert result.language == "de" and result.segments[0].text == "Hallo"
    assert result.segments[0].start == 0.5 and result.model == "converted-turbo"
    save_cached(tmp_path / "cache", "abc", result)
    cached = load_cached(tmp_path / "cache", "abc", registry_id="ct2", model="converted-turbo")
    assert cached and cached.meta["provider"] == "faster-whisper"
    assert load_cached(tmp_path / "cache", "abc", model="mlx-weights") is None


def test_voice_refuses_incomplete_snapshot(tmp_path):
    row = SimpleNamespace(
        status="ready",
        local_path=str(tmp_path),
        runtime="faster-whisper",
        id="ct2",
        repo_id="converted-turbo",
    )
    assert stt_for(Settings(), row) is None


def test_digital_silence_is_not_hallucinated(tmp_path, monkeypatch):
    for name in ("config.json", "model.bin", "tokenizer.json"):
        (tmp_path / name).touch()

    def forbidden(*args, **kwargs):
        pytest.fail("silence must not run inference")

    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=forbidden))
    monkeypatch.setattr(
        "app.knowledge.ingest.faster_whisper.read_wav_mono16k", lambda path: (np.zeros(16000), 1.0)
    )
    result = FasterWhisperTranscriber(str(tmp_path), registry_id="ct2").transcribe(
        tmp_path / "silent.wav"
    )
    assert result.segments == [] and result.duration_s == 1.0
