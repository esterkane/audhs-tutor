"""Owner-enabled authoring scope; never changes the study router or provider defaults."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.kernel import preferences
from app.models_ai import registry
from app.models_ai.gateway import GatewayResult, ModelGateway
from app.models_ai.openai import OpenAIProvider, supported_model
from app.models_ai.provider import Message, TaskClass
from app.models_ai.routing import Router
from app.models_ai.source_policy import authoring_scope


class _AuthoringRouter(Router):
    def __init__(self, identity: str) -> None:
        self.identity = identity

    def chain_for(self, task: TaskClass, override: str | None = None) -> list[str]:
        return [self.identity]

    async def override_for(
        self, db: AsyncSession, task: TaskClass, learner_id: str | None
    ) -> str | None:
        return None


class AuthoringGateway:
    def __init__(self, gateway: ModelGateway, learner_id: str, draft_id: str, version: int) -> None:
        self.gateway = gateway
        self.learner_id, self.draft_id, self.version = learner_id, draft_id, version

    async def complete(
        self, task: TaskClass, messages: list[Message], **kwargs: Any
    ) -> GatewayResult:
        identity = self.gateway.router.chain_for(task)[0]
        with authoring_scope(identity, messages) as digest:
            kwargs["metadata"] = {
                **kwargs.get("metadata", {}),
                "authoring_receipt": {
                    "learner_id": self.learner_id,
                    "draft_id": self.draft_id,
                    "draft_version": self.version,
                    "input_sha256": digest,
                },
            }
            return await self.gateway.complete(task, messages, **kwargs)


async def choose(
    gateway: ModelGateway, settings: Settings | None, learner_id: str, draft_id: str, version: int
) -> ModelGateway | AuthoringGateway:
    values = await preferences.get_all(gateway.db, learner_id)
    if not values.get("authoring.enabled"):
        from app.models_ai.budget import Budget

        return ModelGateway(
            gateway.db,
            gateway.router,
            {k: v for k, v in gateway.providers.items() if k == "ollama"},
            Budget(0),
        )
    cap = int(values.get("authoring.daily_budget_cents", 0)) / 100
    if cap <= 0:
        raise AppError(
            "authoring_budget_missing", "Set a daily authoring budget before using OpenAI.", 409
        )
    identity = str(values["authoring.model"])
    try:
        spec = await registry.get_spec(gateway.db, identity)
    except KeyError as exc:
        raise AppError("authoring_model_invalid", "Choose a registered OpenAI model.", 409) from exc
    if (
        spec.provider != "openai"
        or not supported_model(spec.model)
        or spec.price_in_per_mtok <= 0
        or spec.price_out_per_mtok <= 0
    ):
        raise AppError("authoring_model_invalid", "Choose an OpenAI authoring model.", 409)
    provider = gateway.providers.get("openai")
    if provider is None:
        key = settings.read_authoring_key() if settings else ""
        if not key:
            raise AppError(
                "authoring_key_missing", "Add your OpenAI API key in Authoring setup.", 409
            )
        provider = OpenAIProvider(key)
    # Key presence is transport readiness, not a teaching-quality certification.
    from app.db.models import ModelRegistry

    row = await gateway.db.get(ModelRegistry, identity)
    if row is not None:
        row.status = "ready"
        await gateway.db.flush()
    hosted = ModelGateway(
        gateway.db, _AuthoringRouter(identity), {"openai": provider}, gateway.budget.with_cap(cap)
    )
    return AuthoringGateway(hosted, learner_id, draft_id, version)
