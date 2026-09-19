"""TaskClass -> registry id resolution (ADR-0001/0010). Defaults from routing_profiles.yaml,
runtime overrides from learner_preference `routing.<task>`."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LearnerPreference, ModelRegistry
from app.models_ai.provider import TaskClass

PROFILES_PATH = Path(__file__).with_name("routing_profiles.yaml")


class Route(BaseModel):
    task: TaskClass
    registry_id: str
    chain: list[str]
    position: int  # index in chain; 0 = primary (or learner override)
    override: bool = False

    @property
    def kind(self) -> str:
        return "primary" if self.position == 0 else "fallback"


class NoModelReady(Exception):
    pass


def load_profiles(path: Path = PROFILES_PATH) -> dict[str, Any]:
    with path.open() as f:
        data: dict[str, Any] = yaml.safe_load(f)
    return data


class Router:
    def __init__(self, profile: str = "default", path: Path = PROFILES_PATH) -> None:
        data = load_profiles(path)
        if profile not in data["profiles"]:
            raise KeyError(f"routing profile {profile!r} not in {path}")
        self.profile_name = profile
        self._profile: dict[str, dict[str, Any]] = data["profiles"][profile]

    def chain_for(self, task: TaskClass, override: str | None = None) -> list[str]:
        entry = self._profile.get(str(task))
        if entry is None:
            raise KeyError(f"no routing entry for task {task}")
        chain = [entry["primary"], *entry.get("fallbacks", [])]
        if override:
            chain = [override, *[c for c in chain if c != override]]
        return chain

    async def override_for(
        self, db: AsyncSession, task: TaskClass, learner_id: str | None
    ) -> str | None:
        if learner_id is None:
            return None
        stmt = select(LearnerPreference.value_json).where(
            LearnerPreference.learner_id == learner_id, LearnerPreference.key == f"routing.{task}"
        )
        value = (await db.execute(stmt)).scalar_one_or_none()
        return str(value) if value else None

    async def resolve(
        self,
        db: AsyncSession,
        task: TaskClass,
        learner_id: str | None = None,
        *,
        skip: set[str] | None = None,
    ) -> Route:
        override = await self.override_for(db, task, learner_id)
        chain = self.chain_for(task, override)
        stmt = select(ModelRegistry.id).where(
            ModelRegistry.id.in_(chain), ModelRegistry.status == "ready"
        )
        ready = set((await db.execute(stmt)).scalars().all())
        for pos, rid in enumerate(chain):
            if rid in ready and rid not in (skip or set()):
                return Route(
                    task=task,
                    registry_id=rid,
                    chain=chain,
                    position=pos,
                    override=bool(override) and pos == 0,
                )
        raise NoModelReady(
            f"{task}: none of {chain} is ready (pull/bench/assign via scripts/models.py)"
        )
