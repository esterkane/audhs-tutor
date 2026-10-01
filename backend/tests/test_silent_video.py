import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from app.knowledge.ingest import converters
from app.knowledge.ingest.service import classify


def test_silent_video_never_reaches_decoder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(converters, "find_tool", lambda _: "/fake/ffprobe")
    monkeypatch.setattr(
        converters.subprocess,
        "run",
        Mock(
            return_value=subprocess.CompletedProcess(
                [], 0, json.dumps({"streams": [{"codec_type": "video"}]}).encode(), b""
            )
        ),
    )
    decode = Mock()
    monkeypatch.setattr(converters, "_run", decode)
    with pytest.raises(converters.NoAudioTrack) as exc:
        converters.decode_to_wav(tmp_path / "clip.mp4", tmp_path / "out.wav", "ffmpeg")
    assert classify(exc.value) == "no_content"
    decode.assert_not_called()


@pytest.mark.parametrize(
    "streams",
    [
        [],
        [{"codec_type": "audio"}],
        [{"codec_type": "video"}, {"codec_type": "audio"}],
        None,
        ["invalid"],
        [{"codec_type": "video"}, {}],
        [{"codec_type": "video"}, {"codec_type": "unknown"}],
    ],
)
def test_unproven_silence_keeps_decoder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, streams: object
) -> None:
    monkeypatch.setattr(converters, "find_tool", lambda _: "/fake/tool")
    monkeypatch.setattr(
        converters.subprocess,
        "run",
        Mock(
            return_value=subprocess.CompletedProcess(
                [], 0, json.dumps({"streams": streams}).encode(), b""
            )
        ),
    )
    decode = Mock()
    monkeypatch.setattr(converters, "_run", decode)
    converters.decode_to_wav(tmp_path / "clip.mp4", tmp_path / "out.wav", "ffmpeg")
    decode.assert_called_once()


@pytest.mark.parametrize("failure", [OSError("missing"), subprocess.TimeoutExpired("ffprobe", 30)])
def test_probe_failure_does_not_hide_decode_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    monkeypatch.setattr(converters, "find_tool", lambda _: "/fake/tool")
    monkeypatch.setattr(converters.subprocess, "run", Mock(side_effect=failure))
    monkeypatch.setattr(converters, "_run", Mock(side_effect=RuntimeError("decoder failed")))
    with pytest.raises(RuntimeError, match="decoder failed"):
        converters.decode_to_wav(tmp_path / "clip.mp4", tmp_path / "out.wav", "ffmpeg")


@pytest.mark.parametrize(
    "result",
    [
        subprocess.CompletedProcess([], 1, b"{}", b"bad file"),
        subprocess.CompletedProcess([], 0, b"not json", b""),
    ],
)
def test_invalid_probe_response_keeps_decoder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, result: subprocess.CompletedProcess[bytes]
) -> None:
    monkeypatch.setattr(converters, "find_tool", lambda _: "/fake/tool")
    monkeypatch.setattr(converters.subprocess, "run", Mock(return_value=result))
    decode = Mock()
    monkeypatch.setattr(converters, "_run", decode)
    converters.decode_to_wav(tmp_path / "clip.mp4", tmp_path / "out.wav", "ffmpeg")
    decode.assert_called_once()
