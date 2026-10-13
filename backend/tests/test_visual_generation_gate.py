import pytest
from pydantic import BaseModel

from app.core.errors import AppError
from app.models_ai import registry
from app.models_ai.budget import Budget
from app.models_ai.fake import FakeProvider
from app.models_ai.gateway import ModelGateway
from app.models_ai.provider import Message, TaskClass
from app.models_ai.routing import Router
from tests.test_visual_generation import reserve


class Output(BaseModel):
    label: str


@pytest.mark.parametrize("structured", [False, True])
async def test_gate_covers_fallback_and_repairs(db, learner, session_factory, structured):
    repo, _, row = await reserve(db, learner, session_factory, attempt_limit=1)
    token = await repo.claim(learner.id, row.id)
    await registry.seed_defaults(db, installed_ollama_tags={"gemma3:12b", "llama3.1:8b"})
    provider = FakeProvider(
        fail_structured_times=1 if structured else 0,
        fail_times=0 if structured else 1,
        structured={"label": "example"},
    )
    gateway = ModelGateway(db, Router("default"), {"ollama": provider}, Budget(0))

    async def gate():
        if not await repo.take_attempt(learner.id, row.id, token):
            raise AppError("stopped", "Generation stopped", 409)

    with pytest.raises(AppError, match="Generation stopped"):
        await gateway.complete(
            TaskClass.FORMAT,
            [Message(role="user", content="synthetic")],
            response_model=Output if structured else None,
            learner_id=learner.id,
            before_attempt=gate,
        )
    assert len(provider.calls) == 1


async def test_cancelled_gate_prevents_first_provider_call(db, learner, session_factory):
    repo, _, row = await reserve(db, learner, session_factory)
    token = await repo.claim(learner.id, row.id)
    await registry.seed_defaults(db, installed_ollama_tags={"gemma3:12b"})
    await repo.cancel(learner.id, row.id)
    provider = FakeProvider()
    gateway = ModelGateway(db, Router("default"), {"ollama": provider}, Budget(0))

    async def gate():
        if not await repo.take_attempt(learner.id, row.id, token):
            raise AppError("stopped", "Generation stopped", 409)

    with pytest.raises(AppError):
        await gateway.complete(
            TaskClass.FORMAT,
            [Message(role="user", content="synthetic")],
            learner_id=learner.id,
            before_attempt=gate,
        )
    assert not provider.calls
