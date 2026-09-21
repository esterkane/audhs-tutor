"""Course-material stage 2: guarded WAV normalisation (every PCM/float depth, channel count and
rate reaches the STT adapter as 16 kHz mono 16-bit; the original bytes stay untouched; compressed
variants and oversized files are refused with the ffmpeg hint) and the bounded, versioned vision
cache (successful and explicit no-content answers are reused across documents and archives, keyed
by image bytes + MIME + model identity + prompt version; failures are never reused; corrupt
entries are misses; hits are recorded as free model calls). Synthetic data only, no runtime
models, no live database."""

import hashlib
import io
import json
import math
import struct
import wave
import zipfile
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ModelCall
from app.knowledge.ingest import vision
from app.knowledge.ingest.media import (
    MAX_WAV_BYTES,
    TranscriptResult,
    load_cached,
    normalize_wav,
    probe_wav,
    read_wav_mono16k,
    save_cached,
    transcribe_media,
)
from app.knowledge.ingest.service import IngestOptions, classify, ingest_path
from app.knowledge.ingest.vision import (
    VisionOutput,
    load_vision_cached,
    read_image,
    save_vision_cached,
    vision_cache_key,
)
from app.knowledge.repository import RetrievalRepository
from tests.test_media_ingest import FakeImageReader, FakeTranscriber, make_png

# ----------------------------------------------------------------------------- WAV fixtures


def _sine(rate: int, seconds: float, freq: float = 440.0) -> list[float]:
    return [math.sin(2 * math.pi * freq * i / rate) for i in range(int(rate * seconds))]


def make_wav_bytes(
    *,
    rate: int = 16000,
    channels: int = 1,
    bits: int = 16,
    seconds: float = 0.5,
    fmt: str = "pcm",
    extensible: bool = False,
    amplitude: float = 0.5,
) -> bytes:
    """A RIFF/WAVE file with exactly the header layout a course author's export would have."""
    samples = _sine(rate, seconds)
    frames = bytearray()
    for v in samples:
        x = v * amplitude
        for _ in range(channels):
            if fmt == "float32":
                frames += struct.pack("<f", x)
            elif fmt == "float64":
                frames += struct.pack("<d", x)
            elif bits == 8:
                frames += struct.pack("<B", int(round(x * 127)) + 128)
            elif bits == 16:
                frames += struct.pack("<h", int(round(x * 32767)))
            elif bits == 24:
                n = int(round(x * 8388607)) & 0xFFFFFF
                frames += struct.pack("<I", n)[:3]
            elif bits == 32:
                frames += struct.pack("<i", int(round(x * 2147483647)))
    if fmt == "float32":
        bits, tag = 32, 3
    elif fmt == "float64":
        bits, tag = 64, 3
    elif fmt == "adpcm":
        tag = 2
    else:
        tag = 1
    block = channels * bits // 8
    if extensible:
        guid = struct.pack("<H", tag) + b"\x00\x00\x00\x00\x10\x00\x80\x00\x00\xaa\x00\x38\x9b\x71"
        fmt_body = struct.pack("<HHIIHH", 0xFFFE, channels, rate, rate * block, block, bits)
        fmt_body += struct.pack("<HHI", 22, bits, 0) + guid
    else:
        fmt_body = struct.pack("<HHIIHH", tag, channels, rate, rate * block, block, bits)
    data = bytes(frames)
    body = b"WAVE" + b"fmt " + struct.pack("<I", len(fmt_body)) + fmt_body
    body += b"data" + struct.pack("<I", len(data)) + data
    return b"RIFF" + struct.pack("<I", len(body)) + body


def _rms(audio) -> float:  # type: ignore[no-untyped-def]
    import numpy as np

    return float(np.sqrt(np.mean(np.square(audio)))) if len(audio) else 0.0


@pytest.mark.parametrize(
    ("kwargs", "label"),
    [
        ({"bits": 16}, "pcm16 16000 Hz 1ch"),
        ({"bits": 24, "rate": 48000, "channels": 2}, "pcm24 48000 Hz 2ch"),
        ({"bits": 24, "rate": 44100, "extensible": True}, "pcm24 44100 Hz 1ch"),
        ({"bits": 32, "rate": 22050}, "pcm32 22050 Hz 1ch"),
        ({"bits": 8}, "pcm8 16000 Hz 1ch"),
        (
            {"fmt": "float32", "rate": 48000, "channels": 2, "extensible": True},
            "float32 48000 Hz 2ch",
        ),
        ({"fmt": "float64"}, "float64 16000 Hz 1ch"),
    ],
)
def test_normalize_wav_every_depth_channel_and_rate(
    tmp_path: Path, kwargs: dict, label: str
) -> None:  # type: ignore[type-arg]
    src = tmp_path / "in.wav"
    original = make_wav_bytes(seconds=0.5, **kwargs)
    src.write_bytes(original)
    info, _off, _size = probe_wav(src)
    assert info.label == label and abs(info.duration_s - 0.5) < 0.01
    out = tmp_path / "out.wav"
    got = normalize_wav(src, out)
    assert got.label == label
    with wave.open(str(out), "rb") as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (16000, 1, 2)
    audio, duration = read_wav_mono16k(out)
    assert abs(duration - 0.5) < 0.01
    # the signal survived: a 0.5-amplitude sine has RMS ≈ 0.354 whatever the input depth
    assert 0.30 < _rms(audio) < 0.40, _rms(audio)
    assert src.read_bytes() == original  # the original is only ever read


def test_wav_guards_refuse_what_the_model_must_not_see(tmp_path: Path) -> None:
    src = tmp_path / "adpcm.wav"
    src.write_bytes(make_wav_bytes(fmt="adpcm", bits=4))
    with pytest.raises(RuntimeError, match="needs ffmpeg"):
        normalize_wav(src, tmp_path / "o.wav")
    assert classify(RuntimeError("WAV format 0x2 (compressed) needs ffmpeg")) == "retryable_error"
    bad = tmp_path / "not.wav"
    bad.write_bytes(b"RIFF\x00\x00\x00\x00WAVEjunk")
    with pytest.raises(ValueError, match="fmt/data"):
        probe_wav(bad)
    # 16-bit stays the only thing the adapter reads
    src16 = tmp_path / "s.wav"
    src16.write_bytes(make_wav_bytes(bits=24))
    with pytest.raises(ValueError, match="16-bit"):
        read_wav_mono16k(src16)
    # streaming writers leave the data size unset: the rest of the file is the data
    open_ended = bytearray(make_wav_bytes(bits=16, seconds=0.25))
    pos = open_ended.index(b"data") + 4
    open_ended[pos : pos + 4] = b"\xff\xff\xff\xff"
    (tmp_path / "open.wav").write_bytes(bytes(open_ended))
    info, _o, size = probe_wav(tmp_path / "open.wav")
    assert abs(info.duration_s - 0.25) < 0.01 and size == 8000


def test_normalization_bound_is_enforced_without_loading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.knowledge.ingest.media.MAX_WAV_BYTES", 10_000)
    src = tmp_path / "big.wav"
    src.write_bytes(make_wav_bytes(seconds=1.0))  # 32 000 data bytes > bound
    with pytest.raises(RuntimeError, match="normalisation bound"):
        normalize_wav(src, tmp_path / "o.wav")
    assert MAX_WAV_BYTES > 1_000_000_000  # the real bound is large


def test_transcribe_media_normalises_wav_and_reports_provenance(tmp_path: Path) -> None:
    src = tmp_path / "talk.wav"
    src.write_bytes(make_wav_bytes(bits=24, rate=48000, channels=2, seconds=0.75))
    tr = FakeTranscriber()
    (tmp_path / "work").mkdir()
    res = transcribe_media(
        src, tr, content_hash="h1", cache_dir=tmp_path / "cache", workdir=tmp_path / "work"
    )
    assert tr.calls == 1
    assert res.decoder == "wav-normalise" and res.source_format == "pcm24 48000 Hz 2ch"
    assert abs(res.duration_s - 0.75) < 0.02
    # cached: same provenance comes back, the transcriber is not called again
    again = transcribe_media(
        src, tr, content_hash="h1", cache_dir=tmp_path / "cache", workdir=tmp_path / "work"
    )
    assert again.cached and again.source_format == "pcm24 48000 Hz 2ch" and tr.calls == 1


def test_transcript_cache_is_model_aware_and_survives_corruption(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    res = TranscriptResult(segments=[], model="whisper-a", registry_id="stt-a", duration_s=1.0)
    save_cached(cache, "h", res)
    assert load_cached(cache, "h", registry_id="stt-a", model="whisper-a") is not None
    assert load_cached(cache, "h", registry_id="stt-b", model="whisper-b") is None  # model change
    assert load_cached(cache, "h") is not None  # no model to redo it: any cached text is fine
    (cache / "h.json").write_text("{not json")
    assert load_cached(cache, "h") is None
    (cache / "h.json").write_text(json.dumps({"cache_version": 1, "segments": [{"bogus": 1}]}))
    assert load_cached(cache, "h") is None  # malformed segment: miss, not a crash
    src = tmp_path / "a.wav"
    src.write_bytes(make_wav_bytes())
    (tmp_path / "w").mkdir()
    tr = FakeTranscriber()
    # --retranscribe bypasses the cache and overwrites the corrupt entry
    got = transcribe_media(
        src, tr, content_hash="h", cache_dir=cache, workdir=tmp_path / "w", use_cache=False
    )
    assert tr.calls == 1 and not got.cached
    assert load_cached(cache, "h", registry_id="fake-stt", model="fake-whisper") is not None


# ----------------------------------------------------------------------------- vision cache


def test_vision_cache_reuses_success_and_no_content_but_never_failures(tmp_path: Path) -> None:
    img = tmp_path / "slide.png"
    make_png(img)
    cache = tmp_path / "vcache"
    reader = FakeImageReader("Attention\nQ K V\nDescription: a diagram.")
    blocks, meta = read_image(img, reader, workdir=tmp_path, cache_dir=cache)
    assert blocks and meta["vision"]["cached"] is False and reader.calls == 1
    assert (
        meta["vision"]["tokens_in"] == 300
        and meta["vision"]["prompt_version"] == vision.PROMPT_VERSION
    )
    # same bytes under another name → hit: zero tokens, zero latency, same blocks
    other = tmp_path / "copy.png"
    other.write_bytes(img.read_bytes())
    blocks2, meta2 = read_image(other, reader, workdir=tmp_path, cache_dir=cache)
    assert reader.calls == 1 and meta2["vision"]["cached"] is True
    assert meta2["vision"]["tokens_in"] == 0 and meta2["vision"]["latency_ms"] == 0
    assert [b.text for b in blocks2] == [b.text for b in blocks]
    assert meta2["vision"]["cache_key"] == meta["vision"]["cache_key"]
    # an explicit no-content answer is cached too (the model is not asked twice about a blank)
    blank = tmp_path / "blank.png"
    blank.write_bytes(img.read_bytes()[:-1] + b"\x00")  # different bytes
    none_reader = FakeImageReader("NO_CONTENT")
    b1, m1 = read_image(blank, none_reader, workdir=tmp_path, cache_dir=cache)
    b2, m2 = read_image(blank, none_reader, workdir=tmp_path, cache_dir=cache)
    assert b1 == [] and b2 == [] and m1["vision"]["empty"] and m2["vision"]["cached"]
    assert none_reader.calls == 1
    # a failure is never cached: the next attempt calls the model again
    failing = FakeImageReader("RAISE")
    third = tmp_path / "third.png"
    third.write_bytes(img.read_bytes()[:-2] + b"\x00\x00")
    from app.knowledge.ingest.types import RuntimeCallFailed

    with pytest.raises(RuntimeCallFailed):
        read_image(third, failing, workdir=tmp_path, cache_dir=cache)
    third_sha = hashlib.sha256(third.read_bytes()).hexdigest()
    assert all(json.loads(p.read_text())["image_sha256"] != third_sha for p in cache.glob("*.json"))
    # a blank 200 reply (evicted model, undecodable image) is a failure too — never "no content"
    blank_reply = FakeImageReader("")
    with pytest.raises(RuntimeCallFailed, match="empty response"):
        read_image(third, blank_reply, workdir=tmp_path, cache_dir=cache)
    assert all(json.loads(p.read_text())["image_sha256"] != third_sha for p in cache.glob("*.json"))
    failing.output = "Recovered text"
    b3, m3 = read_image(third, failing, workdir=tmp_path, cache_dir=cache)
    assert failing.calls == 2 and b3 and m3["vision"]["cached"] is False


def test_vision_cache_invalidates_on_model_prompt_mime_and_corruption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    img = tmp_path / "slide.png"
    make_png(img)
    cache = tmp_path / "vcache"
    reader = FakeImageReader("Text")
    read_image(img, reader, workdir=tmp_path, cache_dir=cache)
    assert reader.calls == 1
    # another model identity → miss
    other_model = FakeImageReader("Text")
    other_model.model = "fake-vision-2"
    read_image(img, other_model, workdir=tmp_path, cache_dir=cache)
    assert other_model.calls == 1
    # a prompt change → miss for everyone
    monkeypatch.setattr(vision, "PROMPT_VERSION", vision.PROMPT_VERSION + 1)
    read_image(img, reader, workdir=tmp_path, cache_dir=cache)
    assert reader.calls == 2
    monkeypatch.undo()
    # corrupt entry → miss and overwritten
    key = vision_cache_key(
        hashlib.sha256(img.read_bytes()).hexdigest(), "image/png", reader.registry_id, reader.model
    )
    entry = cache / f"{key}.json"
    assert entry.is_file()
    entry.write_text("{corrupt")
    read_image(img, reader, workdir=tmp_path, cache_dir=cache)
    assert reader.calls == 3 and json.loads(entry.read_text())["text"] == "Text"
    # a tampered entry whose fields do not match is a miss too; so is another MIME for the
    # same bytes (the model answers differently for a JPEG re-encode of the slide)
    payload = json.loads(entry.read_text())
    good = dict(
        image_sha=payload["image_sha256"], registry_id=reader.registry_id, model=reader.model
    )
    assert load_vision_cached(cache, key, mime="image/png", **good) is not None
    assert load_vision_cached(cache, key, mime="image/jpeg", **good) is None
    payload["model"] = "someone-else"
    entry.write_text(json.dumps(payload))
    assert load_vision_cached(cache, key, mime="image/png", **good) is None
    # use_cache=False (--retranscribe) asks the model although a valid entry exists
    read_image(img, reader, workdir=tmp_path, cache_dir=cache)
    calls = reader.calls
    read_image(img, reader, workdir=tmp_path, cache_dir=cache, use_cache=False)
    assert reader.calls == calls + 1


def test_vision_cache_is_bounded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache = tmp_path / "vcache"
    monkeypatch.setattr(vision, "_CACHE_SWEEP_EVERY", 1)
    out = VisionOutput(text="x" * 100)
    for i in range(30):
        save_vision_cached(
            cache,
            f"k{i:03d}",
            out,
            image_sha=f"sha{i}",
            mime="image/png",
            registry_id="r",
            model="m",
            max_entries=10,
            max_bytes=10**9,
        )
    names = sorted(p.name for p in cache.glob("*.json"))
    assert len(names) <= 10 and names[-1] == "k029.json"  # newest kept, oldest dropped
    for i in range(8):
        save_vision_cached(
            cache,
            f"b{i}",
            out,
            image_sha="s",
            mime="m",
            registry_id="r",
            model="m",
            max_entries=10**6,
            max_bytes=1000,
        )
    entries = list(cache.glob("*.json"))
    total = sum(p.stat().st_size for p in entries)
    assert total <= 1000 and 2 <= len(entries) <= 3, (total, len(entries))
    assert (cache / "b7.json").exists()  # the entry just written is never the one evicted


async def test_repeated_images_across_archives_hit_the_cache_and_are_accounted(
    db: AsyncSession, fake_repo: RetrievalRepository, tmp_path: Path
) -> None:
    root = tmp_path / "Udemy"
    sec = root / "Vision Course" / "01 - Slides"
    sec.mkdir(parents=True)
    make_png(tmp_path / "one.png")
    png_bytes = (tmp_path / "one.png").read_bytes()
    for name in ("001 - deck-a.zip", "002 - deck-b.zip"):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("slides/intro.png", png_bytes)
        (sec / name).write_bytes(buf.getvalue())
    reader = FakeImageReader("Attention\nQ K V")
    cache = tmp_path / "vcache"
    opts = IngestOptions(image_reader=reader, vision_cache=cache, media=True)
    report = await ingest_path(db, root, repo=fake_repo, options=opts)
    assert reader.calls == 1  # the second archive's identical slide came from the cache
    assert report.summary()["outcomes"]["imported"] == 2  # two documents, two provenances
    calls = (await db.execute(select(ModelCall).where(ModelCall.task == "vision"))).scalars().all()
    assert len(calls) == 2
    real = [c for c in calls if not c.cached]
    hit = [c for c in calls if c.cached]
    assert len(real) == 1 and len(hit) == 1
    assert real[0].tokens_in == 300 and hit[0].tokens_in == 0 and hit[0].latency_ms == 0
    assert hit[0].metadata_json["cache_key"] == real[0].metadata_json["cache_key"]
    # the cost view counts the hit apart from the calls: one vision call, one cache hit
    from app.models_ai.budget import Budget
    from app.models_ai.usage import cost_report, report_dict

    rep = report_dict(await cost_report(db, Budget(1.0)))
    vision_row = next(b for b in rep["by_task"] if b["key"] == "vision")
    assert vision_row["calls"] == 1 and vision_row["cache_hits"] == 1
    assert rep["window"]["cache_hits"] == 1 and rep["window"]["free_calls"] == 1


async def test_stopped_media_run_resumes_without_transcribing_twice(
    db: AsyncSession, fake_repo: RetrievalRepository, tmp_path: Path
) -> None:
    root = tmp_path / "Udemy"
    sec = root / "Audio Course" / "01 - Talks"
    sec.mkdir(parents=True)
    (sec / "001 - a.wav").write_bytes(make_wav_bytes(bits=24, rate=48000, channels=2))
    (sec / "002 - b.wav").write_bytes(make_wav_bytes(bits=16, seconds=0.75))
    tr = FakeTranscriber()
    calls = 0

    def stop_after_one() -> bool:
        nonlocal calls
        calls += 1
        return calls > 1

    first = await ingest_path(
        db,
        root,
        repo=fake_repo,
        options=IngestOptions(
            transcriber=tr, transcript_cache=tmp_path / "tcache", should_stop=stop_after_one
        ),
    )
    assert first.interrupted and tr.calls == 1 and first.run_id
    second = await ingest_path(
        db,
        root,
        repo=fake_repo,
        options=IngestOptions(transcriber=tr, transcript_cache=tmp_path / "tcache"),
        resume_run_id=first.run_id,
    )
    assert not second.interrupted and second.resumed == 1 and tr.calls == 2
    assert len(second.results) == 1 and second.results[0].transcribed_seconds == pytest.approx(
        0.8, abs=0.05
    )
    stt = (await db.execute(select(ModelCall).where(ModelCall.task == "stt"))).scalars().all()
    assert len(stt) == 2 and {c.metadata_json["source_format"] for c in stt} == {
        "pcm24 48000 Hz 2ch",
        "pcm16 16000 Hz 1ch",
    }


def test_wav_outside_the_inprocess_path_uses_the_external_decoder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The converter boundary stays: a compressed WAV is decoded by ffmpeg/afconvert when one is
    installed (like an mp3 would be) and only refused with the hint when none is."""
    from app.knowledge.ingest import media as media_mod

    src = tmp_path / "adpcm.wav"
    src.write_bytes(make_wav_bytes(fmt="adpcm", bits=4))
    decoded: list[tuple[Path, Path, str]] = []

    def fake_decode(a: Path, b: Path, decoder: str) -> None:
        decoded.append((a, b, decoder))
        b.write_bytes(make_wav_bytes(bits=16, seconds=0.5))

    monkeypatch.setattr(media_mod, "decode_to_wav", fake_decode)
    tr = FakeTranscriber()
    (tmp_path / "w").mkdir()
    res = transcribe_media(
        src, tr, content_hash="c", cache_dir=None, workdir=tmp_path / "w", decoder="ffmpeg"
    )
    assert decoded and decoded[0][2] == "ffmpeg" and res.decoder == "ffmpeg"
    assert res.source_format == "tag0x2/4bit 16000 Hz 1ch via ffmpeg"
    with pytest.raises(RuntimeError, match="needs ffmpeg"):
        transcribe_media(
            src, tr, content_hash="c2", cache_dir=None, workdir=tmp_path / "w", decoder=""
        )
    # oversized PCM likewise goes to the decoder instead of being loaded
    monkeypatch.setattr(media_mod, "MAX_WAV_BYTES", 1000)
    big = tmp_path / "big.wav"
    big.write_bytes(make_wav_bytes(bits=16, seconds=1.0))
    res = transcribe_media(
        big, tr, content_hash="c3", cache_dir=None, workdir=tmp_path / "w", decoder="afconvert"
    )
    assert decoded[-1][2] == "afconvert" and res.source_format == "pcm16 16000 Hz 1ch via afconvert"


def test_long_wav_is_normalised_block_wise_with_continuous_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Overlap-save across block edges: the output has the exact length and no seam."""
    import numpy as np

    from app.knowledge.ingest import media as media_mod

    monkeypatch.setattr(media_mod, "_BLOCK_FRAMES", 4000)  # tiny blocks → many edges
    monkeypatch.setattr(media_mod, "_RESAMPLE_PAD", 512)
    src = tmp_path / "long.wav"
    src.write_bytes(make_wav_bytes(bits=16, rate=44100, channels=2, seconds=2.0, amplitude=0.5))
    out = tmp_path / "out.wav"
    normalize_wav(src, out)
    audio, duration = read_wav_mono16k(out)
    assert abs(duration - 2.0) < 0.01 and len(audio) == 32000
    # the 440 Hz sine keeps its amplitude in every 0.1 s window: no dips at block seams
    for start in range(0, len(audio) - 1600, 1600):
        window = audio[start : start + 1600]
        assert 0.30 < _rms(window) < 0.40, (start, _rms(window))
    # a float file with NaN/Inf samples does not crash and stays within range
    nasty = bytearray(make_wav_bytes(fmt="float32", seconds=0.1))
    pos = nasty.index(b"data") + 8
    nasty[pos : pos + 4] = struct.pack("<f", float("nan"))
    nasty[pos + 4 : pos + 8] = struct.pack("<f", float("inf"))
    (tmp_path / "nasty.wav").write_bytes(bytes(nasty))
    normalize_wav(tmp_path / "nasty.wav", tmp_path / "n.wav")
    audio, _ = read_wav_mono16k(tmp_path / "n.wav")
    assert np.all(np.isfinite(audio)) and float(np.max(np.abs(audio))) <= 1.0
