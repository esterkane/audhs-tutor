"""Wire providers, router, budget and gateway from Settings (no module singletons)."""

from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.events import EventWriter
from app.models_ai.budget import Budget
from app.models_ai.claude import ClaudeProvider
from app.models_ai.gateway import ModelGateway
from app.models_ai.ollama import OllamaProvider
from app.models_ai.provider import ModelProvider
from app.models_ai.routing import Router, load_profiles


def build_providers(settings: Settings) -> dict[str, ModelProvider]:
    providers: dict[str, ModelProvider] = {"ollama": OllamaProvider(settings.ollama_host)}
    if settings.anthropic_api_key:
        providers["anthropic"] = ClaudeProvider(settings.anthropic_api_key)
    return providers


def build_gateway(
    db: AsyncSession, settings: Settings, events: EventWriter | None = None
) -> ModelGateway:
    return ModelGateway(
        db,
        Router(settings.routing_profile),
        build_providers(settings),
        Budget(settings.daily_budget_usd),
        events,
    )


async def installed_ollama_tags(host: str) -> set[str]:
    """Tags Ollama reports as installed; empty set if Ollama is down."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{host.rstrip('/')}/api/tags")
            r.raise_for_status()
    except httpx.HTTPError:
        return set()
    models: list[dict[str, Any]] = r.json().get("models", [])
    return {m["name"] for m in models}


def fastembed_cached(models_dir: Path, repo_id: str) -> set[str]:
    """`fastembed:<repo_id>` when the cross-encoder snapshot exists under MODELS_DIR/fastembed."""
    snap = models_dir / "fastembed" / ("models--" + repo_id.replace("/", "--"))
    return {f"fastembed:{repo_id}"} if snap.is_dir() else set()


async def installed_models(settings: Settings) -> set[str]:
    """Ollama tags + cached fastembed rerankers + 'hosted' when an API key exists (for seeding)."""
    installed = await installed_ollama_tags(settings.ollama_host)
    for entry in load_profiles()["registry_defaults"]:
        if entry.get("runtime") == "fastembed":
            installed |= fastembed_cached(settings.models_dir_resolved, str(entry["repo_id"]))
    if settings.anthropic_api_key:
        installed.add("hosted")
    return installed
