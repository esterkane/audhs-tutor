"""Model registry (ADR-0010): rows in model_registry, seeded from routing_profiles.yaml.

Download/bench/assign live in downloader.py / bench.py and are wired by scripts/models.py.
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LearnerPreference, ModelRegistry
from app.models_ai.provider import ModelSpec, TaskClass
from app.models_ai.routing import PROFILES_PATH, load_profiles

RUNTIME_TO_PROVIDER = {
    "ollama": "ollama",
    "hosted": "anthropic",
    "openai": "openai",
    "mlx": "mlx",
    "fastembed": "fastembed",
    "kokoro": "kokoro",
    "onnx": "onnx",
}


def spec_from_row(row: ModelRegistry) -> ModelSpec:
    # HF GGUF models are imported into Ollama under the registry id (`ollama create <id>`).
    model = row.id if row.source == "huggingface_gguf" else (row.file_or_tag or row.repo_id)
    return ModelSpec(
        registry_id=row.id,
        provider=RUNTIME_TO_PROVIDER.get(row.runtime, row.runtime),
        model=model,
        price_in_per_mtok=row.price_in_per_mtok or 0.0,
        price_out_per_mtok=row.price_out_per_mtok or 0.0,
        context_len=row.context_len,
    )


async def get_row(db: AsyncSession, registry_id: str) -> ModelRegistry:
    row = await db.get(ModelRegistry, registry_id)
    if row is None:
        raise KeyError(f"model {registry_id!r} not in registry")
    return row


async def get_spec(db: AsyncSession, registry_id: str) -> ModelSpec:
    return spec_from_row(await get_row(db, registry_id))


async def list_models(db: AsyncSession) -> Sequence[ModelRegistry]:
    return (await db.execute(select(ModelRegistry).order_by(ModelRegistry.id))).scalars().all()


async def upsert(db: AsyncSession, data: dict[str, Any]) -> ModelRegistry:
    row = await db.get(ModelRegistry, data["id"])
    if row is None:
        row = ModelRegistry(**data)
        db.add(row)
    else:
        for k, v in data.items():
            setattr(row, k, v)
    await db.commit()
    return row


async def seed_defaults(
    db: AsyncSession, path: Path = PROFILES_PATH, *, installed_ollama_tags: set[str] | None = None
) -> list[ModelRegistry]:
    """Insert registry_defaults that are missing. Ollama tags already installed are marked ready;
    hosted entries are ready when an API key exists (caller decides via installed set 'hosted')."""
    rows: list[ModelRegistry] = []
    installed = installed_ollama_tags or set()
    for entry in load_profiles(path)["registry_defaults"]:
        existing = await db.get(ModelRegistry, entry["id"])
        if existing is not None:
            rows.append(existing)
            continue
        status = "available"
        if entry["runtime"] == "ollama" and _tag_installed(entry["file_or_tag"], installed):
            status = "ready"
        if entry["runtime"] in ("hosted", "openai") and entry["runtime"] in installed:
            status = "ready"
        if entry["runtime"] == "fastembed" and f"fastembed:{entry['repo_id']}" in installed:
            status = "ready"
        if entry["runtime"] == "mlx" and f"mlx:{entry['repo_id']}" in installed:
            status = "ready"
        if entry["runtime"] == "kokoro" and "kokoro" in installed:
            status = "ready"
        if entry["runtime"] == "onnx" and f"onnx:{entry['repo_id']}" in installed:
            status = "ready"
        row = ModelRegistry(**entry, status=status)
        db.add(row)
        rows.append(row)
    await db.commit()
    return rows


def _tag_installed(tag: str, installed: set[str]) -> bool:
    return tag in installed or f"{tag}:latest" in installed


async def set_status(
    db: AsyncSession, registry_id: str, status: str, **fields: Any
) -> ModelRegistry:
    row = await get_row(db, registry_id)
    row.status = status
    for k, v in fields.items():
        setattr(row, k, v)
    await db.commit()
    return row


async def assign(db: AsyncSession, learner_id: str, task: TaskClass, registry_id: str) -> None:
    """Persist a learner routing override. Refuses unbenchmarked or non-ready models."""
    row = await get_row(db, registry_id)
    if row.status != "ready":
        raise ValueError(f"{registry_id} is {row.status}, not ready — pull it first")
    if not row.benchmark_json:
        raise ValueError(
            f"{registry_id} has no benchmark — run `models.py bench {registry_id}` first"
        )
    key = f"routing.{task}"
    stmt = select(LearnerPreference).where(
        LearnerPreference.learner_id == learner_id, LearnerPreference.key == key
    )
    pref = (await db.execute(stmt)).scalar_one_or_none()
    if pref is None:
        db.add(
            LearnerPreference(
                learner_id=learner_id, key=key, value_json=registry_id, origin="explicit"
            )
        )
    else:
        pref.value_json = registry_id
        pref.origin = "explicit"
    await db.commit()
