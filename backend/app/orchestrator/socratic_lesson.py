"""Buffer the small structured lesson turn; never stream JSON or an unvalidated question."""

from collections.abc import AsyncGenerator
from typing import Any

from app.db.events import EventWriter
from app.models_ai.gateway import ModelGateway, StreamHandle
from app.models_ai.provider import Message, TaskClass
from app.schemas.socratic import SocraticLessonProbe, SocraticLessonReply


async def stream_reply(
    gateway: ModelGateway,
    messages: list[Message],
    *,
    handle: StreamHandle,
    learner_id: str,
    session_id: str,
    metadata: dict[str, Any],
    max_tokens: int,
    events: EventWriter,
    question_only: bool = False,
) -> AsyncGenerator[str, None]:
    response_model = SocraticLessonProbe if question_only else SocraticLessonReply
    result = await gateway.complete(
        TaskClass.EXPLAIN_SIMPLE,
        messages,
        response_model=response_model,
        learner_id=learner_id,
        session_id=session_id,
        metadata=metadata,
        max_tokens=max_tokens,
        events=events,
    )
    # Populate the normal tutor accounting/trace handle before rendering or yielding.
    handle.model_call_id = result.model_call_id
    handle.registry_id = result.registry_id
    handle.route = result.route
    handle.request_id = result.request_id
    handle.cost_usd = result.cost_usd
    handle.usage_source = result.usage_source
    handle.cost_status = result.cost_status
    handle.tokens_in = result.result.tokens_in
    handle.tokens_out = result.result.tokens_out
    handle.cached_tokens = result.result.cached_tokens
    handle.latency_ms = result.result.latency_ms
    handle.finish_reason = result.result.finish_reason
    reply = response_model.model_validate(result.result.parsed)
    yield reply.render()
