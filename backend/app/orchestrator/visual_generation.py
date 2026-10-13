"""Explicit local generation of a reserved Ask graph; never called on a read/render."""

import asyncio
import json
from contextlib import suppress

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError
from app.db.models import Chunk, ChunkProvenance
from app.kernel.answer_visual_binding import validate_answer_binding
from app.kernel.authored_visuals import canonical, digest, require_current_trust
from app.kernel.visual_generation import GenerationRequests, owned
from app.models_ai.gateway import ModelGateway
from app.models_ai.provider import TaskClass
from app.orchestrator.context import ContextPacket, RetrievedChunk, escape_data, render_messages
from app.orchestrator.prompts import _read
from app.schemas.answer_visual_binding import AnswerVisualBinding
from app.schemas.authored_visuals import AnswerRelationshipVisual
from app.schemas.visual_generation import GraphProposal

PROMPT_VERSION = "ask.visual.v1"
MAX_INPUT_BYTES = 48_000


async def _inputs(
    factory: async_sessionmaker[AsyncSession], owner: str, identity: str, threshold: int
) -> tuple[AnswerVisualBinding, ContextPacket]:
    # Fresh consistent read; release it before inference or any writer transaction.
    async with factory() as db:
        await db.execute(text("BEGIN"))
        row = await owned(db, owner, identity)
        if row.prompt_version != PROMPT_VERSION:
            raise AppError("visual_prompt_changed", "Create a new visual request.", 409)
        binding = AnswerVisualBinding.model_validate_json(row.binding_json)
        resolved = await validate_answer_binding(db, owner, binding)
        if resolved.grounding == "unknown":
            raise AppError("visual_source_changed", "The answer's sources need review.", 409)
        ids = frozenset(s.chunk_id for c in resolved.source_checks.values() for s in c.sources)
        if len(ids) > 64:
            raise AppError("visual_input_large", "This answer has too many visual sources.", 422)
        await require_current_trust(db, ids, threshold)
        chunks = list(await db.scalars(select(Chunk).where(Chunk.id.in_(ids)).order_by(Chunk.id)))
        provenance = {
            p.chunk_id: p
            for p in await db.scalars(
                select(ChunkProvenance).where(ChunkProvenance.chunk_id.in_(ids))
            )
        }
        history = json.loads(resolved.snapshot_json)["answers"]
        root = next(item for item in history if item["id"] == binding.answer_id)
        packet = ContextPacket(
            policy=_read("ask/visual.v1.md"),
            historical=[
                {
                    "question": root["request_json"]["question"],
                    "answer": root["text"],
                    "learning_purpose": binding.learning_purpose or "",
                }
            ],
            retrieved=[
                RetrievedChunk(
                    chunk_id=c.id,
                    text=c.text,
                    citation=f"source ID: {escape_data(c.id)}",
                    trust_tier=provenance[c.id].trust_tier,
                    score=1,
                )
                for c in chunks
            ],
            request="Explain the saved answer as a relationship diagram; return graph JSON.",
            prompt_version=PROMPT_VERSION,
        )
        if (
            sum(
                len(m.content.encode()) for m in render_messages(packet, include_source_trust=False)
            )
            > MAX_INPUT_BYTES
        ):
            raise AppError("visual_input_large", "Choose a shorter answer for a visual.", 422)
        return binding, packet


async def generate(
    factory: async_sessionmaker[AsyncSession],
    gateway: ModelGateway,
    owner: str,
    identity: str,
    *,
    quarantine_below_trust: int = 2,
) -> str | None:
    """Use a dedicated gateway session. Duplicate/terminal starts perform no inference."""
    requests = GenerationRequests(factory)
    token = await requests.claim(owner, identity)
    if token is None:
        async with factory() as db:
            return (await owned(db, owner, identity)).result_version_id
    try:
        binding, packet = await _inputs(factory, owner, identity, quarantine_below_trust)

        async def gate() -> None:
            # Recheck source currency/trust before every repair and fallback as well.
            await _inputs(factory, owner, identity, quarantine_below_trust)
            if not await requests.take_attempt(owner, identity, token):
                raise AppError("generation_stopped", "Visual generation stopped.", 409)

        result = await gateway.complete(
            TaskClass.FORMAT,
            render_messages(packet, include_source_trust=False),
            response_model=GraphProposal,
            learner_id=owner,
            max_tokens=4096,
            temperature=0.1,
            before_attempt=gate,
            metadata={
                "surface": "ask_visual",
                "generation_id": identity,
                "binding_sha256": digest(canonical(binding.model_dump(mode="json"))),
                "prompt_version": PROMPT_VERSION,
            },
        )
        if not isinstance(result.result.parsed, GraphProposal):
            raise AppError("invalid_visual", "The model did not return a valid diagram.", 422)
        spec = AnswerRelationshipVisual.model_validate_json(
            canonical(
                {
                    **result.result.parsed.model_dump(mode="json"),
                    "schema_version": "visual.answer.v1",
                    "kind": "relationship",
                    "binding": binding.model_dump(mode="json"),
                }
            )
        )
        return await requests.complete(
            owner,
            identity,
            token,
            spec,
            result.model_call_id,
            quarantine_below_trust=quarantine_below_trust,
        )
    except asyncio.CancelledError:
        with suppress(AppError):  # A concurrent learner wipe must not resurrect the request.
            await requests.cancel(owner, identity)
        raise
    except Exception:
        with suppress(AppError):
            await requests.fail(owner, identity, token)
        raise
