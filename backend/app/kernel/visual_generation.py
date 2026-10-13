"""Durable reservations and atomic worker publication; no inference in the kernel."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError
from app.db.base import new_id, utcnow_iso
from app.db.models import ModelCall
from app.db.models import VisualGenerationRequest as Generation
from app.db.traces import TutorTraceRecord, write_tutor_trace
from app.kernel.answer_visual_binding import validate_answer_binding
from app.kernel.authored_visuals import (
    VisualRepository,
    canonical,
    digest,
    require_current_trust,
    resolve_target,
)
from app.schemas.answer_visual_binding import AnswerVisualBinding
from app.schemas.authored_visuals import (
    AnswerRelationshipVisual,
    SaveVisual,
    VisualOrigin,
    parse_command,
)


async def owned(db: AsyncSession, owner: str, identity: str) -> Generation:
    row = await db.scalar(
        select(Generation).where(Generation.id == identity, Generation.learner_id == owner)
    )
    if row is None:
        raise AppError("not_found", "Visual generation request unavailable.", 404)
    return row


class GenerationRequests:
    def __init__(self, factory: async_sessionmaker[AsyncSession]):
        self.factory = factory

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[AsyncSession]:
        async with self.factory() as db:
            try:
                await db.execute(text("BEGIN IMMEDIATE"))
                yield db
                await db.commit()
            except BaseException:
                await db.rollback()
                raise

    async def reserve(
        self,
        owner: str,
        key: str,
        binding: AnswerVisualBinding,
        prompt_version: str,
        *,
        attempt_limit: int = 3,
    ) -> Generation:
        if (
            not key.strip()
            or len(key) > 128
            or not prompt_version.strip()
            or len(prompt_version) > 128
        ):
            raise ValueError("Invalid request or prompt identity")
        if type(attempt_limit) is not int or not 1 <= attempt_limit <= 3:
            raise ValueError("Invalid attempt limit")
        payload = canonical(
            {
                "binding": binding.model_dump(mode="json"),
                "prompt_version": prompt_version,
                "attempt_limit": attempt_limit,
            }
        )
        fingerprint = digest(payload)
        async with self.transaction() as db:
            prior = await db.scalar(
                select(Generation).where(
                    Generation.learner_id == owner, Generation.request_key == key
                )
            )
            if prior:
                if prior.fingerprint != fingerprint:
                    raise AppError(
                        "request_conflict", "Request identity already has different inputs.", 409
                    )
                return prior
            await validate_answer_binding(db, owner, binding)
            row = Generation(
                learner_id=owner,
                request_key=key,
                fingerprint=fingerprint,
                binding_json=canonical(binding.model_dump(mode="json")),
                prompt_version=prompt_version,
                attempt_limit=attempt_limit,
            )
            db.add(row)
            await db.flush()
            return row

    async def claim(self, owner: str, identity: str) -> str | None:
        async with self.transaction() as db:
            row = await owned(db, owner, identity)
            if row.state != "pending":
                return None
            row.state, row.worker_token, row.updated_at = "running", new_id(), utcnow_iso()
            return row.worker_token

    async def take_attempt(self, owner: str, identity: str, token: str) -> bool:
        """A worker must call before EVERY provider attempt, including repairs/fallbacks."""
        async with self.transaction() as db:
            row = await owned(db, owner, identity)
            if row.state != "running" or row.worker_token != token:
                return False
            if row.attempts >= row.attempt_limit:
                row.state, row.error_code, row.worker_token = "failed", "attempt_limit", None
                row.updated_at = utcnow_iso()
                return False
            row.attempts += 1
            row.updated_at = utcnow_iso()
            return True

    async def cancel(self, owner: str, identity: str) -> Generation:
        async with self.transaction() as db:
            row = await owned(db, owner, identity)
            if row.state in {"pending", "running"}:
                row.state, row.worker_token, row.updated_at = "cancelled", None, utcnow_iso()
            return row

    async def fail(self, owner: str, identity: str, token: str) -> bool:
        async with self.transaction() as db:
            row = await owned(db, owner, identity)
            if row.state != "running" or row.worker_token != token:
                return False
            row.state, row.error_code, row.worker_token = "failed", "generation_failed", None
            row.updated_at = utcnow_iso()
            return True

    async def interrupt_abandoned(self) -> int:
        """Startup only in the single-server process; never called by status reads."""
        async with self.transaction() as db:
            result = await db.execute(
                update(Generation)
                .where(Generation.state.in_(["pending", "running"]))
                .values(
                    state="interrupted",
                    worker_token=None,
                    error_code="server_restart",
                    updated_at=utcnow_iso(),
                )
            )
            return int(result.rowcount)  # type: ignore[attr-defined]

    async def complete(
        self,
        owner: str,
        identity: str,
        token: str,
        spec: AnswerRelationshipVisual,
        model_call_id: str,
        *,
        quarantine_below_trust: int = 2,
    ) -> str:
        """Trusted worker only: publish version and terminal result in ONE transaction."""
        async with self.transaction() as db:
            row = await owned(db, owner, identity)
            if row.state == "completed" and row.result_version_id:
                return row.result_version_id
            if row.state != "running" or row.worker_token != token or row.attempts < 1:
                raise AppError("generation_stopped", "Generation is no longer active.", 409)
            if canonical(spec.binding.model_dump(mode="json")) != row.binding_json:
                raise AppError(
                    "generation_changed", "Visual target does not match the request.", 409
                )
            call = await db.scalar(
                select(ModelCall).where(
                    ModelCall.id == model_call_id, ModelCall.learner_id == owner
                )
            )
            expected = {
                "surface": "ask_visual",
                "generation_id": identity,
                "binding_sha256": digest(row.binding_json),
                "prompt_version": row.prompt_version,
            }
            if (
                call is None
                or not call.ok
                or call.outcome != "ok"
                or call.provider != "ollama"
                or call.task != "format"
                or any(call.metadata_json.get(k) != v for k, v in expected.items())
            ):
                raise AppError(
                    "generation_call_mismatch", "Model result does not match this request.", 409
                )
            target = await resolve_target(db, owner, spec)
            if target.grounding == "unknown":
                raise AppError(
                    "generation_grounding_changed", "Grounding is incomplete or changed.", 409
                )
            await require_current_trust(db, target.source_ids, quarantine_below_trust)
            command = SaveVisual(action="save", expected_revision=0, spec=spec)
            try:
                parse_command(canonical(command.model_dump(mode="json")).encode())
            except ValueError:
                raise AppError(
                    "invalid_visual", "Visual exceeds the validated content limits.", 422
                ) from None
            receipt = await VisualRepository(self.factory)._save(
                db,
                owner,
                None,
                command,
                VisualOrigin(
                    kind="model", model=call.registry_id, prompt_version=row.prompt_version
                ),
            )
            await write_tutor_trace(
                db,
                TutorTraceRecord(
                    learner_id=owner,
                    session_id=None,
                    turn_id=identity,
                    action="ask_visual",
                    prompt_version=row.prompt_version,
                    model_call_id=call.id,
                    latency_ms=call.latency_ms,
                ),
                commit=False,
            )
            assert receipt.version_id is not None
            row.result_version_id = receipt.version_id
            row.state, row.worker_token, row.updated_at = "completed", None, utcnow_iso()
            return receipt.version_id
