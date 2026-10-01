"""Registry-backed optional ingest helpers: the speech-to-text model (`TaskClass.STT`) and the
vision model for slide images (`TaskClass.VISION`). Both resolve through the router like every
other model and refuse when the artefact is missing — ingest never downloads anything.
`default_options()` is the one place the API and the CLI build an `IngestOptions`."""

import asyncio
import importlib.util
import platform
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.knowledge.ingest.archives import ARCHIVE_SUFFIXES
from app.knowledge.ingest.converters import find_decoder, find_tool, legacy_office_tool
from app.knowledge.ingest.media import AUDIO_SUFFIXES, VIDEO_SUFFIXES, MlxWhisperTranscriber
from app.knowledge.ingest.service import IngestOptions
from app.knowledge.ingest.vision import IMAGE_SUFFIXES, OllamaImageReader
from app.models_ai import registry
from app.models_ai.factory import mlx_snapshot_dir
from app.models_ai.provider import TaskClass
from app.models_ai.routing import NoModelReady, Router


def route_primary(settings: Settings, task: TaskClass) -> str | None:
    """The registry id the routing profile names first for `task` (for user-facing hints)."""
    try:
        return Router(settings.routing_profile).chain_for(task)[0]
    except (KeyError, IndexError):
        return None


def pull_hint(settings: Settings, task: TaskClass, what: str) -> str:
    rid = route_primary(settings, task)
    if rid is None:
        return f"no {what} model is routed for `{task.value}` in routing_profiles.yaml"
    return f'no ready {what} model — Models › pull {rid} (make models args="pull {rid}")'


async def transcriber_for(db: AsyncSession, settings: Settings) -> MlxWhisperTranscriber | None:
    try:
        route = await Router(settings.routing_profile).resolve(db, TaskClass.STT)
    except (NoModelReady, KeyError):
        return None
    row = await registry.get_row(db, route.registry_id)
    if row.runtime != "mlx":
        return None
    local = (
        Path(row.local_path)
        if row.local_path
        else mlx_snapshot_dir(settings.models_dir_resolved, row.repo_id)
    )
    if not await asyncio.to_thread((local / "config.json").exists):
        return None  # registry says ready but the snapshot is gone: never download at ingest time
    return MlxWhisperTranscriber(str(local), registry_id=row.id, model=row.repo_id)


async def image_reader_for(db: AsyncSession, settings: Settings) -> OllamaImageReader | None:
    try:
        route = await Router(settings.routing_profile).resolve(db, TaskClass.VISION)
    except (NoModelReady, KeyError):
        return None
    row = await registry.get_row(db, route.registry_id)
    if row.runtime != "ollama":
        return None
    spec = registry.spec_from_row(row)
    return OllamaImageReader(settings.ollama_host, spec.model, registry_id=row.id)


def stt_package_installed() -> bool:
    return importlib.util.find_spec("mlx_whisper") is not None


async def default_options(
    db: AsyncSession,
    settings: Settings,
    *,
    media: bool = True,
    language: str | None = None,
    force_media: bool = False,
) -> IngestOptions:
    """Resolve the optional runtimes once per run. With `media=False` nothing is resolved and
    media/images are listed as skipped."""
    return IngestOptions(
        transcriber=await transcriber_for(db, settings) if media else None,
        image_reader=await image_reader_for(db, settings) if media else None,
        language=language or settings.stt_language or None,
        media=media,
        force_media=force_media,
        transcript_cache=settings.transcript_cache_dir_resolved,
        vision_cache=settings.vision_cache_dir_resolved,
        stt_hint=pull_hint(settings, TaskClass.STT, "speech-to-text"),
        vision_hint=pull_hint(settings, TaskClass.VISION, "vision"),
    )


async def capabilities(db: AsyncSession, settings: Settings) -> dict[str, Any]:
    """What this machine can ingest right now, with the next step for what it cannot."""
    from app.knowledge.ingest.loaders import FORMAT_GROUPS, KNOWN_UNSUPPORTED

    transcriber = await transcriber_for(db, settings)
    reader = await image_reader_for(db, settings)
    decoder = find_decoder()
    stt_pkg = stt_package_installed()
    if transcriber is None:
        stt_detail = pull_hint(settings, TaskClass.STT, "speech-to-text")
    elif not stt_pkg:
        stt_detail = (
            f"{transcriber.registry_id} is pulled; install the Python extra: uv sync --group stt"
        )
    elif decoder is None:
        stt_detail = f"{transcriber.registry_id} ready; no audio decoder — brew install ffmpeg"
    else:
        stt_detail = f"{transcriber.registry_id} ready via {decoder}" + (
            " (afconvert: mp3/m4a/mp4/mov/wav/flac; ogg/opus/mkv/webm need ffmpeg)"
            if decoder == "afconvert"
            else ""
        )
    return {
        "formats": FORMAT_GROUPS,
        "unsupported": KNOWN_UNSUPPORTED,
        "archives": sorted(ARCHIVE_SUFFIXES),
        "audio": sorted(AUDIO_SUFFIXES),
        "video": sorted(VIDEO_SUFFIXES),
        "images": sorted(IMAGE_SUFFIXES),
        "stt": {
            "ready": transcriber is not None and stt_pkg and decoder is not None,
            "registry_id": transcriber.registry_id if transcriber else None,
            "package_installed": stt_pkg,
            "detail": stt_detail,
        },
        "vision": {
            "ready": reader is not None,
            "registry_id": reader.registry_id if reader else None,
            "detail": (
                f"{reader.registry_id} ready via Ollama"
                if reader
                else pull_hint(settings, TaskClass.VISION, "vision") + " (multimodal)"
            ),
        },
        "audio_decoder": decoder,
        "legacy_office": legacy_office_tool(),
        "image_converter": "sips" if platform.system() == "Darwin" and find_tool("sips") else None,
    }
