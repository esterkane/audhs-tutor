"""media-transcription slice: fake STT / vision runtimes (no MLX, no network), WAV built in-test,
sidecar rule, transcript cache, hash pre-check, model_call rows, registry readiness, routes."""

import math
import platform
import shutil
import struct
import wave
import zlib
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models import ModelCall
from app.knowledge.ingest.converters import decode_to_wav
from app.knowledge.ingest.loaders import load_file, source_type_for
from app.knowledge.ingest.media import (
    Segment,
    TranscriptResult,
    load_cached,
    read_wav_mono16k,
    sidecar_transcript,
    transcribe_media,
    transcript_to_blocks,
)
from app.knowledge.ingest.runtime import (
    capabilities,
    default_options,
    image_reader_for,
    transcriber_for,
)
from app.knowledge.ingest.service import IngestOptions, ingest_path
from app.knowledge.ingest.types import RuntimeCallFailed
from app.knowledge.ingest.vision import VisionOutput, image_blocks
from app.knowledge.sqlite_hybrid import SqliteHybridRepository
from app.models_ai import registry
from app.models_ai.factory import mlx_cached, mlx_snapshot_dir
from app.models_ai.provider import TaskClass
from app.models_ai.routing import Router


def make_wav(path: Path, *, seconds: float = 1.0, rate: int = 16000, channels: int = 1) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        n = int(rate * seconds)
        frames = b"".join(
            struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / rate))) * channels
            for i in range(n)
        )
        w.writeframes(frames)


def make_png(path: Path) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    raw = b"\x00\xff\xff\xff"  # one white pixel, filter 0
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)


class FakeTranscriber:
    model = "fake-whisper"
    registry_id = "fake-stt"

    def __init__(self) -> None:
        self.calls = 0
        self.languages: list[str | None] = []

    def transcribe(self, wav: Path, *, language: str | None = None) -> TranscriptResult:
        self.calls += 1
        self.languages.append(language)
        _, duration = read_wav_mono16k(wav)
        return TranscriptResult(
            segments=[
                Segment(0.0, 0.5, "Attention weights the values."),
                Segment(0.5, 1.0, "Attention weights the values."),  # Whisper repeat → deduped
                Segment(1.0, 1.5, "Softmax makes them sum to one."),
            ],
            language=language or "en",
            model=self.model,
            registry_id=self.registry_id,
            duration_s=duration,
            latency_ms=12,
        )


class FakeImageReader:
    model = "fake-vision"
    registry_id = "fake-vision"

    def __init__(self, output: str) -> None:
        self.output = output
        self.calls = 0

    def read(self, image: bytes, *, mime: str) -> VisionOutput:
        self.calls += 1
        assert image.startswith(b"\x89PNG") and mime == "image/png"
        if self.output == "RAISE":
            raise ConnectionError("ollama down")
        return VisionOutput(text=self.output, latency_ms=7, tokens_in=300, tokens_out=12)


# ----------------------------------------------------------------------------- units
def test_wav_reader_and_blocks(tmp_path: Path) -> None:
    wav = tmp_path / "a.wav"
    make_wav(wav, seconds=0.5, rate=44100, channels=2)
    audio, duration = read_wav_mono16k(wav)
    assert abs(duration - 0.5) < 0.01 and audio.ndim == 1 and len(audio) == 8000
    res = FakeTranscriber().transcribe(wav)
    blocks = transcript_to_blocks(res)
    assert len(blocks) == 1 and blocks[0].kind == "caption" and blocks[0].t_start == 0.0
    assert blocks[0].text == "Attention weights the values. Softmax makes them sum to one."


def test_sidecar_detection(tmp_path: Path) -> None:
    media = tmp_path / "005 - Lecture.mp4"
    media.write_bytes(b"x")
    assert sidecar_transcript(media) is None
    (tmp_path / "005 - Lecture.de.srt").write_text("1\n00:00:01,000 --> 00:00:02,000\nx\n")
    (tmp_path / "005 - Lecture.en.vtt").write_text("WEBVTT\n")
    assert sidecar_transcript(media) is not None and sidecar_transcript(media).name.endswith(
        ".en.vtt"
    )
    lecture_dir = tmp_path / "Lecture 3-1 - 40. Intro"
    lecture_dir.mkdir()
    (lecture_dir / "video.mp4").write_bytes(b"x")
    (lecture_dir / "captions.vtt").write_text("WEBVTT\n")
    assert (
        sidecar_transcript(lecture_dir / "video.mp4") is not None
    )  # any caption in a lecture folder


def test_transcribe_media_cache_and_missing_runtime(tmp_path: Path) -> None:
    wav = tmp_path / "talk.wav"
    make_wav(wav)
    cache = tmp_path / "cache"
    tr = FakeTranscriber()
    res = transcribe_media(
        wav, tr, content_hash="h1", cache_dir=cache, workdir=tmp_path, language="de"
    )
    assert res.language == "de" and tr.calls == 1 and not res.cached
    assert load_cached(cache, "h1") is not None
    res2 = transcribe_media(wav, tr, content_hash="h1", cache_dir=cache, workdir=tmp_path)
    assert res2.cached and tr.calls == 1 and res2.segments[0].text == res.segments[0].text
    with pytest.raises(RuntimeError, match="speech-to-text"):
        transcribe_media(wav, None, content_hash="h2", cache_dir=None, workdir=tmp_path)
    mp3 = tmp_path / "talk.ogg"
    mp3.write_bytes(b"OggS")
    with pytest.raises(RuntimeError, match="ffmpeg"):
        transcribe_media(
            mp3, tr, content_hash="h3", cache_dir=None, workdir=tmp_path, decoder="afconvert"
        )
    with pytest.raises(RuntimeError, match="no audio decoder"):
        transcribe_media(mp3, tr, content_hash="h3", cache_dir=None, workdir=tmp_path, decoder="")


@pytest.mark.skipif(
    platform.system() != "Darwin" or shutil.which("afconvert") is None, reason="macOS afconvert"
)
def test_afconvert_decodes_to_16k_mono(tmp_path: Path) -> None:
    src = tmp_path / "stereo.wav"
    make_wav(src, seconds=0.3, rate=44100, channels=2)
    dst = tmp_path / "out.wav"
    decode_to_wav(src, dst, "afconvert")
    with wave.open(str(dst), "rb") as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (16000, 1, 2)


def test_image_blocks_parsing() -> None:
    blocks = image_blocks(
        "Scaled dot-product\nQ K V\nDescription: three matrices feeding a softmax.", heading="s1"
    )
    assert blocks[0].kind == "slide" and blocks[0].text == "Scaled dot-product\nQ K V"
    assert blocks[1].text.startswith("Figure: three matrices")
    assert image_blocks("NO_CONTENT") == [] and image_blocks("  no_content ") == []


# ----------------------------------------------------------------------------- service
async def test_media_ingest_end_to_end(
    db: AsyncSession, fake_repo: SqliteHybridRepository, tmp_path: Path
) -> None:
    root = tmp_path / "courses"  # the transcript cache must live outside the ingested tree
    sec = root / "Course V" / "01 - Talks"
    sec.mkdir(parents=True)
    make_wav(sec / "001 - Intro.wav", seconds=1.5)
    make_wav(sec / "002 - Captioned.wav")
    (sec / "002 - Captioned.en.vtt").write_text(
        "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nfrom the caption\n"
    )
    make_png(sec / "003 - Slide.png")
    make_png(sec / "004 - Blank.png")
    (sec / "005 - Video.mkv").write_bytes(b"\x1aE\xdf\xa3")  # needs ffmpeg → skip reason
    tr = FakeTranscriber()
    reader = FakeImageReader("Attention\nQ K V\nDescription: a diagram of heads.")
    cache = tmp_path / "cache"
    opts = IngestOptions(transcriber=tr, image_reader=reader, transcript_cache=cache, language="en")

    # a blank image needs its own reader answer: run it separately with NO_CONTENT
    blank_opts = IngestOptions(image_reader=FakeImageReader("NO_CONTENT"), media=True)
    blank = await ingest_path(db, sec / "004 - Blank.png", repo=fake_repo, options=blank_opts)
    assert blank.results == [] and "no text or figure" in blank.skipped[0].reason
    empty_call = (await db.execute(select(ModelCall))).scalars().one()  # logged although empty
    assert empty_call.task == "vision" and empty_call.metadata_json["empty"] is True
    await db.execute(ModelCall.__table__.delete())
    await db.commit()
    (sec / "004 - Blank.png").unlink()

    report = await ingest_path(db, root, repo=fake_repo, options=opts)
    names = {Path(r.uri).name: r for r in report.results}
    assert set(names) == {"001 - Intro.wav", "002 - Captioned.en.vtt", "003 - Slide.png"}, (
        report.skipped
    )
    intro = names["001 - Intro.wav"]
    assert intro.source_type == "audio" and intro.transcribed_seconds == pytest.approx(
        1.5, abs=0.05
    )
    assert names["003 - Slide.png"].vision and names["003 - Slide.png"].source_type == "image"
    skipped = {Path(s.path).name: s.reason for s in report.skipped}
    assert skipped["002 - Captioned.wav"] == "transcript present: 002 - Captioned.en.vtt"
    assert "ffmpeg" in skipped["005 - Video.mkv"] or "decoder" in skipped["005 - Video.mkv"]
    assert tr.calls == 1 and tr.languages == ["en"] and reader.calls == 1
    summary = report.summary()
    assert summary["transcribed_media"] == 1 and summary["images_read"] == 1
    assert summary["audio_seconds"] == pytest.approx(1.5, abs=0.05)
    calls = (await db.execute(select(ModelCall).order_by(ModelCall.task))).scalars().all()
    assert [(c.task, c.provider, c.registry_id) for c in calls] == [
        ("stt", "mlx", "fake-stt"),
        ("vision", "ollama", "fake-vision"),
    ]
    assert calls[0].metadata_json["duration_s"] == pytest.approx(1.5, abs=0.05)
    assert calls[1].tokens_in == 300 and calls[1].tokens_out == 12 and calls[1].ok
    # the transcript is citable with timestamps and searchable
    hits = (await fake_repo.search("softmax sum to one", k=3)).hits
    assert any(
        h.chunk.provenance.t_start == 0.0 and h.chunk.provenance.source_type == "audio"
        for h in hits
    )

    # unchanged media: hash pre-check → no decode, no transcriber call, trust re-decision applied
    again = await ingest_path(db, root, repo=fake_repo, options=opts, trust_tier=3)
    assert again.summary()["unchanged"] == 3 and tr.calls == 1 and reader.calls == 1
    assert all(r.trust_updated for r in again.results)
    # media disabled: listed, not decoded
    off = await ingest_path(
        db, tmp_path, repo=fake_repo, options=IngestOptions(media=False), trust_tier=3
    )
    assert {Path(s.path).name for s in off.skipped if "disabled" in s.reason} == {
        "001 - Intro.wav",
        "002 - Captioned.wav",
        "003 - Slide.png",
        "005 - Video.mkv",
    }
    # a changed file with the same content elsewhere reuses the cache instead of transcribing
    copy = sec / "006 - Copy.wav"
    copy.write_bytes((sec / "001 - Intro.wav").read_bytes())
    doc = load_file(copy, root=root, transcriber=tr, transcript_cache=cache)
    assert doc.meta["transcription"]["cached"] is True and tr.calls == 1


async def test_missing_runtimes_are_reported_not_raised(
    db: AsyncSession, fake_repo: SqliteHybridRepository, settings: Settings, tmp_path: Path
) -> None:
    sec = tmp_path / "C" / "S"
    sec.mkdir(parents=True)
    make_wav(sec / "a.wav")
    make_png(sec / "b.png")
    opts = await default_options(db, settings)  # what the API and CLI build: hints name the model
    assert opts.transcriber is None and opts.image_reader is None
    report = await ingest_path(db, tmp_path, repo=fake_repo, options=opts)
    reasons = {Path(s.path).name: s.reason for s in report.skipped}
    assert "pull whisper-large-v3-turbo" in reasons["a.wav"]
    assert "pull gemma3-12b" in reasons["b.png"]
    assert report.results == []


# ----------------------------------------------------------------------------- registry
@pytest.mark.parametrize("package_installed", [False, True])
@pytest.mark.parametrize("decoder", [None, "ffmpeg", "afconvert"])
async def test_stt_registry_readiness_and_routing(
    db: AsyncSession,
    settings: Settings,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    decoder: str | None,
    package_installed: bool,
) -> None:
    monkeypatch.setattr(
        "app.knowledge.ingest.runtime.stt_package_installed", lambda: package_installed
    )
    monkeypatch.setattr("app.knowledge.ingest.runtime.find_decoder", lambda: decoder)
    settings = settings.model_copy(update={"models_dir": str(tmp_path / "models")})
    repo = "mlx-community/whisper-large-v3-turbo"
    assert mlx_cached(settings.models_dir_resolved, repo) == set()
    snap = mlx_snapshot_dir(settings.models_dir_resolved, repo)
    snap.mkdir(parents=True)
    (snap / "config.json").write_text("{}")
    assert mlx_cached(settings.models_dir_resolved, repo) == set()  # config alone is a half pull
    (snap / "weights.safetensors").write_bytes(b"\x00")
    installed = mlx_cached(settings.models_dir_resolved, repo)
    assert installed == {f"mlx:{repo}"}
    rows = await registry.seed_defaults(db, installed_ollama_tags=installed)
    whisper = next(r for r in rows if r.id == "whisper-large-v3-turbo")
    assert whisper.status == "ready" and whisper.role == "stt" and whisper.runtime == "mlx"
    route = await Router(settings.routing_profile).resolve(db, TaskClass.STT)
    assert route.registry_id == "whisper-large-v3-turbo"
    tr = await transcriber_for(db, settings)
    assert (
        tr is not None and tr.registry_id == "whisper-large-v3-turbo" and tr.model_path == str(snap)
    )
    assert await image_reader_for(db, settings) is None  # gemma3-12b not pulled → no vision
    caps = await capabilities(db, settings)
    assert caps["stt"]["registry_id"] == "whisper-large-v3-turbo"
    assert caps["stt"]["package_installed"] is package_installed
    assert caps["audio_decoder"] == decoder
    assert caps["stt"]["ready"] is (caps["stt"]["package_installed"] and decoder is not None)
    (snap / "config.json").unlink()
    assert await transcriber_for(db, settings) is None  # artefact gone → never download at ingest


async def test_ingest_route_media_flags(client: AsyncClient, tmp_path: Path) -> None:
    sec = tmp_path / "R" / "S"
    sec.mkdir(parents=True)
    make_wav(sec / "x.wav")
    r = await client.post("/api/corpus/ingest", json={"path": str(tmp_path), "media": False})
    assert r.status_code == 200, r.text
    assert r.json()["skipped"][0]["reason"] == "media disabled for this run"
    r = await client.post("/api/corpus/ingest", json={"path": str(tmp_path), "language": "de"})
    assert "pull whisper-large-v3-turbo" in r.json()["skipped"][0]["reason"]


async def test_failed_vision_call_is_logged_not_free(
    db: AsyncSession, fake_repo: SqliteHybridRepository, tmp_path: Path
) -> None:
    sec = tmp_path / "C" / "S"
    sec.mkdir(parents=True)
    make_png(sec / "slide.png")
    opts = IngestOptions(image_reader=FakeImageReader("RAISE"))
    report = await ingest_path(db, tmp_path, repo=fake_repo, options=opts)
    assert report.results == [] and "ollama down" in report.skipped[0].reason
    call = (await db.execute(select(ModelCall))).scalars().one()
    assert call.ok is False and call.task == "vision" and "ConnectionError" in (call.error or "")


def test_sidecar_ignores_metadata_json_and_multi_media_folders(tmp_path: Path) -> None:
    media = tmp_path / "lecture.mp4"
    media.write_bytes(b"x")
    (tmp_path / "lecture.json").write_text('{"id": 5, "title": "Lecture"}')  # Udemy metadata
    (tmp_path / "lecture.txt").write_text("A description of the lecture.\nNothing timed.\n")
    assert sidecar_transcript(media) is None
    (tmp_path / "lecture.tsv").write_text("start\tend\ttext\n0\t2000\thello\n2000\t4000\tworld\n")
    assert sidecar_transcript(media) is not None  # a real transcript with a sniffed suffix
    folder = tmp_path / "Lecture 2-1 - 7. Two videos"
    folder.mkdir()
    (folder / "part1.mp4").write_bytes(b"x")
    (folder / "part2.mp4").write_bytes(b"x")
    (folder / "captions.vtt").write_text("WEBVTT\n")
    assert sidecar_transcript(folder / "part2.mp4") is None  # one caption cannot cover two videos
    (folder / "part2.mp4").unlink()
    assert sidecar_transcript(folder / "part1.mp4") is not None


def test_typescript_is_code_not_mpeg_ts() -> None:
    assert source_type_for(Path("app.ts")) == "code" and source_type_for(Path("x.mts")) == "code"
    assert source_type_for(Path("lecture.m2ts")) == "video"


async def test_archive_members_respect_media_gate(
    db: AsyncSession, fake_repo: SqliteHybridRepository, tmp_path: Path
) -> None:
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("talk/a.mp4", b"\x00\x00\x00\x18ftypmp42")
        z.writestr("talk/a.en.vtt", "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nfrom caption\n")
        z.writestr("talk/b.png", b"\x89PNG\r\n\x1a\n")
    (tmp_path / "course.zip").write_bytes(buf.getvalue())
    tr = FakeTranscriber()
    report = await ingest_path(db, tmp_path, repo=fake_repo, options=IngestOptions(transcriber=tr))
    reasons = {Path(s.path).name: s.reason for s in report.skipped}
    assert reasons["a.mp4"] == "transcript present: a.en.vtt" and tr.calls == 0
    assert "vision" in reasons["b.png"]
    assert [Path(r.uri).name for r in report.results] == ["a.en.vtt"]
    off = await ingest_path(db, tmp_path, repo=fake_repo, options=IngestOptions(media=False))
    assert {Path(s.path).name for s in off.skipped if "disabled" in s.reason} == {"a.mp4", "b.png"}


async def test_ingest_route_validates_language(client: AsyncClient, tmp_path: Path) -> None:
    r = await client.post("/api/corpus/ingest", json={"path": str(tmp_path), "language": "English"})
    assert r.status_code == 422


def test_runtime_call_failed_carries_registry_fields() -> None:
    e = RuntimeCallFailed(task="stt", provider="mlx", registry_id="w", model="m", error="boom")
    assert "w" in str(e) and e.task == "stt" and e.latency_ms == 0
