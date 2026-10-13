"""Durable reservations only. Inference and atomic result publication follow separately."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError
from app.db.base import new_id, utcnow_iso
from app.db.models import VisualGenerationRequest as Generation
from app.kernel.answer_visual_binding import validate_answer_binding
from app.kernel.authored_visuals import canonical, digest
from app.schemas.answer_visual_binding import AnswerVisualBinding


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
