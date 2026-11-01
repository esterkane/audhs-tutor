"""Owner-enabled project explanation API; reviewed reuse and accepted reading stay local."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.kernel import preferences
from app.models_ai import registry
from app.models_ai.budget import Budget
from app.models_ai.claude import ClaudeProvider
from app.models_ai.gateway import GatewayResult, ModelGateway
from app.models_ai.openai import OpenAIProvider, supported_model
from app.models_ai.provider import Message, ModelSpec, TaskClass
from app.models_ai.routing import Router, load_profiles
from app.models_ai.study_policy import study_scope


class ProjectStudyRouter(Router):
    def __init__(self, identity: str) -> None:
        self.identity = identity

    def chain_for(self, task: TaskClass, override: str | None = None) -> list[str]:
        return [self.identity]

    async def override_for(
        self, db: AsyncSession, task: TaskClass, learner_id: str | None
    ) -> str | None:
        return None


class ProjectStudyGateway:
    def __init__(self, gateway: ModelGateway, spec: ModelSpec, learner_id: str) -> None:
        self.gateway, self.spec, self.learner_id = gateway, spec, learner_id

    async def complete(
        self, task: TaskClass, messages: list[Message], **kwargs: Any
    ) -> GatewayResult:
        if task != TaskClass.EXPLAIN_SIMPLE:
            raise AppError(
                "study_task_not_allowed",
                "Hosted project study is limited to tutor explanations.",
                409,
            )
        with study_scope(self.spec, messages) as digest:
            kwargs["metadata"] = {
                **kwargs.get("metadata", {}),
                "study_receipt": {
                    "learner_id": self.learner_id,
                    "input_sha256": digest,
                    "scope": "project_explanation",
                    "provider": self.spec.provider,
                },
            }
            return await self.gateway.complete(task, messages, **kwargs)


async def choose_project_study(
    db: AsyncSession,
    settings: Settings,
    learner_id: str,
    providers: dict[str, Any],
    budget: Budget,
) -> ProjectStudyGateway | None:
    values = await preferences.get_all(db, learner_id)
    provider_name = values.get("project.study_provider", "local")
    if provider_name == "local":
        return None
    if provider_name not in {"openai", "anthropic"}:
        raise AppError(
            "study_provider_invalid", "Choose OpenAI, Anthropic or local project study.", 409
        )
    # This is the SAME cap/ledger as authoring, not a second daily allowance.
    cap = int(values.get("authoring.daily_budget_cents", 0)) / 100
    if cap <= 0:
        raise AppError(
            "study_budget_missing",
            "Set the shared daily hosted budget before using API tutoring.",
            409,
        )
    identity = str(values.get("project.study_model", "openai-luna-study"))
    try:
        spec = await registry.get_spec(db, identity)
    except KeyError as exc:
        raise AppError(
            "study_model_invalid", "Choose a registered hosted tutor model.", 409
        ) from exc
    if (
        spec.provider != provider_name
        or spec.price_in_per_mtok <= 0
        or spec.price_out_per_mtok <= 0
    ):
        raise AppError(
            "study_model_invalid",
            "The model must match the selected hosted provider and verified prices.",
            409,
        )
    known = next(
        (entry for entry in load_profiles()["registry_defaults"] if entry["id"] == identity), None
    )
    if (
        known is None
        or identity not in load_profiles().get("project_study_models", [])
        or spec.model != (known.get("file_or_tag") or known["repo_id"])
        or spec.price_in_per_mtok < float(known.get("price_in_per_mtok", 0))
        or spec.price_out_per_mtok < float(known.get("price_out_per_mtok", 0))
        or (spec.context_len or 0) > int(known.get("context_len", 0))
    ):
        raise AppError(
            "study_model_unverified", "The hosted model context and prices need verification.", 409
        )
    provider = providers.get(provider_name)
    if provider_name == "openai":
        if not supported_model(spec.model):
            raise AppError("study_model_invalid", "Choose a supported OpenAI model.", 409)
        if provider is None:
            key = settings.read_authoring_key()
            if not key:
                raise AppError(
                    "study_key_missing",
                    "Add the OpenAI key in Authoring setup before API tutoring.",
                    409,
                )
            provider = OpenAIProvider(key)
    elif provider is None:
        if not settings.anthropic_api_key:
            raise AppError(
                "study_key_missing",
                "Set ANTHROPIC_API_KEY on the backend before Claude API tutoring.",
                409,
            )
        provider = ClaudeProvider(settings.anthropic_api_key)
    row = await registry.get_row(db, identity)
    row.status = "ready"
    await db.flush()
    gateway = ModelGateway(
        db, ProjectStudyRouter(identity), {provider_name: provider}, budget.with_cap(cap)
    )
    return ProjectStudyGateway(gateway, spec, learner_id)
