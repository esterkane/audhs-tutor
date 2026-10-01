"""Model registry operations shared by `scripts/models.py` and the Models settings screen
(ADR-0010): search Hugging Face, add, pull, bench, assign per TaskClass, remove, routing table.
Long-running steps (pull, bench) report progress through a callback and never touch app state;
the API runs them as background jobs, the CLI runs them inline."""

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models import ModelRegistry
from app.models_ai import registry
from app.models_ai.bench import bench_model
from app.models_ai.benchmark_gateway import BenchmarkProvider, BenchmarkRouter
from app.models_ai.budget import Budget
from app.models_ai.downloader import Downloader, dir_size_gb, hf_info, hf_search, slugify
from app.models_ai.factory import build_providers, installed_models, mlx_snapshot_dir
from app.models_ai.gateway import ModelGateway
from app.models_ai.openai import supported_model
from app.models_ai.provider import TaskClass
from app.models_ai.routing import Router

Progress = Callable[[str], None] | None

RUNTIME_FOR_SOURCE = {
    "ollama_library": "ollama",
    "huggingface_gguf": "ollama",
    "huggingface_mlx": "mlx",
    "huggingface_fastembed": "fastembed",
    "hosted": "hosted",
    "openai": "openai",
    "kokoro_server": "kokoro",  # a persistent server the owner starts; nothing is downloaded here
    "huggingface_file": "onnx",  # one file from a HF repo (Silero VAD)
}
ROLES = ("chat", "code", "embed", "rerank", "stt", "tts", "vad", "judge")
KOKORO_SETUP = (
    "Kokoro is a persistent server you start yourself, e.g. "
    "`docker run -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-cpu:latest` (or the MLX build), then "
    "set KOKORO_URL in .env and reload Models. Nothing is downloaded by the app."
)


def _say(progress: Progress, msg: str) -> None:
    if progress:
        progress(msg)


async def seed(db: AsyncSession, settings: Settings) -> list[ModelRegistry]:
    """Insert missing defaults and refresh readiness of local/hosted rows."""
    installed = await installed_models(settings)
    rows = await registry.seed_defaults(db, installed_ollama_tags=installed)
    for r in await registry.list_models(db):
        if r.status not in ("available", "ready"):
            continue
        if r.runtime == "ollama":
            tag = r.id if r.source == "huggingface_gguf" else (r.file_or_tag or r.repo_id)
            r.status = (
                "ready" if (tag in installed or f"{tag}:latest" in installed) else "available"
            )
        elif r.runtime == "hosted":
            r.status = "ready" if settings.anthropic_api_key else "available"
        elif r.runtime == "openai":
            r.status = "ready" if settings.openai_api_key else "available"
        elif r.runtime == "fastembed":
            r.status = "ready" if f"fastembed:{r.repo_id}" in installed else "available"
        elif r.runtime == "mlx":
            r.status = "ready" if f"mlx:{r.repo_id}" in installed else "available"
            if r.status == "ready" and not r.local_path:
                r.local_path = str(mlx_snapshot_dir(settings.models_dir_resolved, r.repo_id))
        elif r.runtime == "kokoro":
            r.status = "ready" if "kokoro" in installed else "available"
        elif r.runtime == "onnx":
            r.status = "ready" if f"onnx:{r.repo_id}" in installed else "available"
            if r.status == "ready" and not r.local_path and r.file_or_tag:
                r.local_path = str(
                    settings.models_dir_resolved / "onnx" / r.id / Path(r.file_or_tag).name
                )
    await db.commit()
    return rows


async def search(
    query: str, *, gguf: bool = False, mlx: bool = False, limit: int = 20
) -> list[dict[str, Any]]:
    return await asyncio.to_thread(hf_search, query, gguf=gguf, mlx=mlx, limit=limit)


async def add(
    db: AsyncSession,
    settings: Settings,
    *,
    source: str,
    repo_id: str,
    file: str | None = None,
    tag: str | None = None,
    registry_id: str | None = None,
    display_name: str | None = None,
    role: str = "chat",
    quant: str | None = None,
    context_len: int | None = None,
    price_in: float = 0.0,
    price_out: float = 0.0,
) -> ModelRegistry:
    if source not in RUNTIME_FOR_SOURCE:
        raise ValueError(f"unknown source {source}; one of {sorted(RUNTIME_FOR_SOURCE)}")
    if role not in ROLES:
        raise ValueError(f"role must be one of {ROLES}")
    if source == "huggingface_gguf" and not file:
        raise ValueError("huggingface_gguf needs a .gguf file name (see model info)")
    if source == "hosted" and not tag:
        raise ValueError("hosted needs a model id tag, e.g. claude-sonnet-5")
    if source == "openai":
        if not tag:
            raise ValueError("openai needs an API model id tag")
        if not supported_model(tag):
            raise ValueError("OpenAI model is not in the verified registry defaults")
        if not (0 < price_in < float("inf") and 0 < price_out < float("inf")):
            raise ValueError("OpenAI needs positive finite input/output prices per million tokens")
    file_or_tag = (
        file or tag or (repo_id if source in ("ollama_library", "huggingface_fastembed") else None)
    )
    rid = registry_id or slugify(repo_id.split("/")[-1], file or tag)
    licence, size_gb = None, None
    if source.startswith("huggingface"):
        try:
            info = await asyncio.to_thread(hf_info, repo_id, settings.hf_token)
            licence = info["licence"]
            match = [f for f in info["gguf_files"] if f["filename"] == file]
            size_gb = match[0]["size_gb"] if match else (info["total_size_gb"] or None)
        except Exception:  # network is optional at add time
            pass
    return await registry.upsert(
        db,
        {
            "id": rid,
            "display_name": display_name or rid,
            "source": source,
            "repo_id": repo_id,
            "file_or_tag": file_or_tag,
            "runtime": RUNTIME_FOR_SOURCE[source],
            "role": role,
            "quant": quant,
            "licence": licence,
            "size_gb": size_gb,
            "context_len": context_len,
            "status": "ready"
            if (
                (source == "hosted" and settings.anthropic_api_key)
                or (source == "openai" and settings.openai_api_key)
            )
            else "available",
            "price_in_per_mtok": price_in,
            "price_out_per_mtok": price_out,
        },
    )


async def pull(
    db: AsyncSession, settings: Settings, registry_id: str, progress: Progress = None
) -> ModelRegistry:
    """Download the artefact for a registry row; status downloading → ready | failed."""
    await registry.seed_defaults(db, installed_ollama_tags=await installed_models(settings))
    row = await registry.get_row(db, registry_id)
    dl = Downloader(settings.ollama_host, settings.models_dir_resolved, settings.hf_token)
    await registry.set_status(db, row.id, "downloading")
    try:
        if row.source == "ollama_library":
            await dl.ollama_pull(row.file_or_tag or row.repo_id, progress)
            await registry.set_status(db, row.id, "ready")
        elif row.source == "huggingface_gguf":
            assert row.file_or_tag
            path = await dl.hf_gguf(
                row.repo_id, row.file_or_tag, row.id, num_ctx=row.context_len, progress=progress
            )
            await registry.set_status(
                db, row.id, "ready", local_path=str(path), size_gb=dir_size_gb(path)
            )
        elif row.source == "huggingface_mlx":
            path = await dl.hf_mlx(row.repo_id, progress)
            await registry.set_status(
                db, row.id, "ready", local_path=str(path), size_gb=dir_size_gb(path)
            )
        elif row.source == "huggingface_fastembed":
            path = await dl.fastembed_cross_encoder(row.repo_id, progress)
            await registry.set_status(
                db, row.id, "ready", local_path=str(path), size_gb=dir_size_gb(path)
            )
        elif row.source in ("hosted", "openai"):
            key_name = "OPENAI_API_KEY" if row.source == "openai" else "ANTHROPIC_API_KEY"
            key = settings.openai_api_key if row.source == "openai" else settings.anthropic_api_key
            if not key:
                raise ValueError(f"set {key_name} in .env and restart the backend first")
            await registry.set_status(db, row.id, "ready")
        elif row.source == "kokoro_server":
            from app.voice.tts import kokoro_reachable

            if not await kokoro_reachable(settings.kokoro_url):
                await registry.set_status(db, row.id, "available")
                raise ValueError(f"no Kokoro server at {settings.kokoro_url}. {KOKORO_SETUP}")
            await registry.set_status(db, row.id, "ready")
        elif row.source == "huggingface_file":
            assert row.file_or_tag
            path = await dl.hf_file(row.repo_id, row.file_or_tag, row.id, progress)
            await registry.set_status(
                db, row.id, "ready", local_path=str(path), size_gb=dir_size_gb(path.parent)
            )
    except Exception as e:
        # a server that is simply not running is not a broken artefact: the row stays available
        await registry.set_status(
            db,
            row.id,
            "available" if row.source in ("kokoro_server", "hosted", "openai") else "failed",
        )
        _say(progress, f"pull failed: {e}")
        raise
    _say(progress, f"{row.id} ready")
    return await registry.get_row(db, row.id)


async def bench_reranker(model: str, cache_dir: Any) -> dict[str, float]:
    import time

    from app.knowledge.rerank import RERANK_MAX_CHARS, FastembedReranker

    rr = FastembedReranker(model, cache_dir=cache_dir)
    body = "Scaled dot-product attention divides the scores by sqrt(d_k) before the softmax. " * 30
    docs = [f"Lecture {i} › Attention\n{body}"[:RERANK_MAX_CHARS] for i in range(16)]
    await rr.score("warm up", docs)
    t0 = time.perf_counter()
    for _ in range(3):
        await rr.score("why divide attention scores by sqrt(d_k)?", docs)
    return {"ms_per_16_docs": round((time.perf_counter() - t0) / 3 * 1000, 1)}


async def bench_stt(local_path: str, registry_id: str) -> dict[str, float]:
    """Ten seconds of synthetic audio through the transcriber: reports wall time per 10 s of
    audio (real-time factor = ms / 10000). Needs the optional `mlx-whisper` extra."""
    import math
    import struct
    import tempfile
    import wave

    from app.knowledge.ingest.media import MlxWhisperTranscriber

    tr = MlxWhisperTranscriber(local_path, registry_id=registry_id)

    def _run() -> dict[str, float]:
        with tempfile.TemporaryDirectory() as td:
            wav = Path(td) / "tone.wav"
            with wave.open(str(wav), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(16000)
                frames = b"".join(
                    struct.pack("<h", int(6000 * math.sin(2 * math.pi * 220 * i / 16000)))
                    for i in range(16000 * 10)
                )
                w.writeframes(frames)
            tr.transcribe(wav)  # warm up (model load)
            res = tr.transcribe(wav)
        return {"ms_per_10s_audio": float(res.latency_ms), "rtf": round(res.latency_ms / 10000, 3)}

    return await asyncio.to_thread(_run)


async def bench(
    db: AsyncSession,
    settings: Settings,
    registry_id: str,
    progress: Progress = None,
    *,
    budget: Budget | None = None,
) -> dict[str, Any]:
    row = await registry.get_row(db, registry_id)
    if row.status != "ready":
        raise ValueError(f"{row.id} is {row.status}; pull it first")
    spec = registry.spec_from_row(row)
    if row.runtime == "fastembed":
        result = await bench_reranker(spec.model, settings.models_dir_resolved / "fastembed")
    elif row.runtime == "mlx" and row.role == "stt":
        local = row.local_path or str(mlx_snapshot_dir(settings.models_dir_resolved, row.repo_id))
        _say(progress, f"transcribing 10 s of audio with {row.id} …")
        result = await bench_stt(local, row.id)
    else:
        provider = build_providers(settings).get(spec.provider)
        if provider is None:
            raise ValueError(
                f"no provider for runtime {row.runtime}; configure its API key and restart"
            )
        _say(progress, f"benchmarking {row.id} …")
        if spec.hosted:
            provider = BenchmarkProvider(
                ModelGateway(
                    db,
                    BenchmarkRouter(row.id),
                    {spec.provider: provider},
                    budget or Budget(settings.daily_budget_usd),
                )
            )
        result = await bench_model(provider, spec)
    await registry.set_status(db, row.id, "ready", benchmark_json=result)
    return result


async def assign(db: AsyncSession, learner_id: str, task: str, registry_id: str) -> None:
    await registry.assign(db, learner_id, TaskClass(task), registry_id)


async def remove(db: AsyncSession, settings: Settings, registry_id: str) -> ModelRegistry:
    row = await registry.get_row(db, registry_id)
    dl = Downloader(settings.ollama_host, settings.models_dir_resolved, settings.hf_token)
    tag = row.id if row.source == "huggingface_gguf" else row.file_or_tag
    await dl.remove(runtime=row.runtime, tag=tag, local_path=row.local_path)
    await registry.set_status(db, row.id, "removed", local_path=None, benchmark_json=None)
    return await registry.get_row(db, row.id)


async def routing_table(
    db: AsyncSession, settings: Settings, learner_id: str
) -> list[dict[str, Any]]:
    """Per TaskClass: the chain (override first), each entry's status, and what would be used."""
    router = Router(settings.routing_profile)
    rows = {r.id: r for r in await registry.list_models(db)}
    out = []
    for task in TaskClass:
        override = await router.override_for(db, task, learner_id)
        chain = router.chain_for(task, override)
        resolved = next(
            (rid for rid in chain if rows.get(rid) and rows[rid].status == "ready"), None
        )
        problem, action = route_problem(chain, rows, settings) if resolved is None else (None, None)
        out.append(
            {
                "task": str(task),
                "override": override,
                "chain": [
                    {"registry_id": rid, "status": rows[rid].status if rid in rows else "unknown"}
                    for rid in chain
                ],
                "resolved": resolved,
                "problem": problem,
                "action": action,
            }
        )
    return out


def route_problem(
    chain: list[str], rows: dict[str, ModelRegistry], settings: Settings
) -> tuple[str, str]:
    """Why a task has no ready model, and the one concrete step that would fix it. When a local
    model in the chain only needs pulling, that is the offered step (cheaper than a hosted key)."""
    first = chain[0] if chain else ""
    local_pull = next(
        (
            rid
            for rid in chain
            if rid in rows
            and rows[rid].runtime not in ("hosted", "openai")
            and rows[rid].status in ("available", "removed")
        ),
        None,
    )
    row = rows.get(first)
    if row is None:
        return (
            f"{first} is not in the registry",
            f"add {first} under Models (or fix routing_profiles.yaml)",
        )
    if row.runtime in ("hosted", "openai"):
        key_name = "OPENAI_API_KEY" if row.runtime == "openai" else "ANTHROPIC_API_KEY"
        key = settings.openai_api_key if row.runtime == "openai" else settings.anthropic_api_key
        if not key:
            problem = f"{first} is hosted and {key_name} is empty"
            if local_pull:
                return (
                    problem,
                    f"pull {local_pull} under Models (local fallback), or set {key_name} in .env",
                )
            return problem, f"set {key_name} in .env and restart the backend"
        return f"{first} is {row.status}", "check the API key and network, then reload Models"
    if row.status == "downloading":
        return f"{first} is still downloading", "wait for the download to finish (Models › jobs)"
    if row.status in ("available", "removed"):
        return (
            f"{first} is not downloaded",
            f"pull {first} under Models (nothing downloads without your click)",
        )
    return f"{first} is {row.status}", f"pull or re-add {first} under Models"
