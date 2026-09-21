"""In-app daily hosted budget (ADR-0001), P6 edition: reserve → call → reconcile.

What counts toward today's cap (UTC day):
  reported/estimated/legacy hosted `model_call.cost_usd`
  + `reserved_usd` of hosted calls whose billing is **unknown** (failed with no usage: the provider
    may have billed us — counted at the worst case, never as free)
  + open, unexpired reservations (calls in flight).
Reservations bound the worst case up front (prompt estimate + `max_tokens` at the registry price),
so concurrent calls cannot overshoot the cap between check and log. A reservation older than
RESERVATION_TTL_S is stale (the process died mid-call) and is marked `expired` on the next check.
The lock serialises reserve-and-check inside one process; SQLite rows are the truth across processes
(Phase 1 runs one backend process — a second process could overshoot by one reservation).
"""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BudgetReservation, ModelCall
from app.models_ai.provider import HOSTED_PROVIDERS

RESERVATION_TTL_S = 600
COUNTED_STATUSES = ("reported", "estimated", "legacy")
CHARS_PER_TOKEN_BOUND = 3  # reservation bound: German/code/JSON-heavy prompts run ~3 chars/token


class BudgetExceeded(Exception):
    def __init__(self, spent: float, cap: float) -> None:
        super().__init__(f"daily hosted budget exceeded: spent ${spent:.4f} of ${cap:.2f}")
        self.spent = spent
        self.cap = cap


def today_start_iso() -> str:
    now = datetime.now(UTC)
    return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat(timespec="milliseconds")


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class Spend:
    cap: float
    reported: float = 0.0
    estimated: float = 0.0
    legacy: float = 0.0
    unknown_reserved: float = 0.0
    open_reservations: float = 0.0

    @property
    def counted(self) -> float:
        return round(
            self.reported
            + self.estimated
            + self.legacy
            + self.unknown_reserved
            + self.open_reservations,
            6,
        )

    @property
    def remaining(self) -> float:
        return round(max(self.cap - self.counted, 0.0), 6)


class Budget:
    def __init__(self, daily_cap_usd: float, *, lock: asyncio.Lock | None = None) -> None:
        self.daily_cap_usd = daily_cap_usd
        self._lock = lock or asyncio.Lock()

    async def expire_stale(self, db: AsyncSession) -> int:
        """Open reservations past their TTL are stale (process died mid-call) → `expired`."""
        res = await db.execute(
            update(BudgetReservation)
            .where(
                BudgetReservation.status == "open",
                BudgetReservation.expires_at < _now().isoformat(timespec="milliseconds"),
            )
            .values(status="expired")
        )
        n = int(getattr(res, "rowcount", 0) or 0)
        if n:
            await db.commit()
        return n

    async def spend_today(self, db: AsyncSession) -> Spend:
        since = today_start_iso()
        spend = Spend(cap=self.daily_cap_usd)
        rows = (
            await db.execute(
                select(ModelCall.cost_status, func.coalesce(func.sum(ModelCall.cost_usd), 0.0))
                .where(ModelCall.ts >= since, ModelCall.provider.in_(HOSTED_PROVIDERS))
                .group_by(ModelCall.cost_status)
            )
        ).all()
        for status, total in rows:
            if status in ("reported", "estimated", "legacy"):
                setattr(spend, str(status), float(total))
        spend.unknown_reserved = float(
            (
                await db.execute(
                    select(func.coalesce(func.sum(ModelCall.reserved_usd), 0.0)).where(
                        ModelCall.ts >= since,
                        ModelCall.provider.in_(HOSTED_PROVIDERS),
                        ModelCall.cost_status == "unknown",
                    )
                )
            ).scalar_one()
        )
        spend.open_reservations = float(
            (
                await db.execute(
                    select(func.coalesce(func.sum(BudgetReservation.amount_usd), 0.0)).where(
                        BudgetReservation.status == "open",
                        BudgetReservation.expires_at >= _now().isoformat(timespec="milliseconds"),
                    )
                )
            ).scalar_one()
        )
        return spend

    async def check(self, db: AsyncSession, projected_usd: float = 0.0) -> float:
        """Raise if today's counted spend (+ projected) would reach the cap; return spend so far."""
        await self.expire_stale(db)
        spend = await self.spend_today(db)
        if spend.counted + projected_usd >= self.daily_cap_usd:
            raise BudgetExceeded(spend.counted, self.daily_cap_usd)
        return spend.counted

    async def reserve(
        self,
        db: AsyncSession,
        *,
        request_id: str,
        registry_id: str,
        task: str,
        amount_usd: float,
        learner_id: str | None,
    ) -> BudgetReservation:
        """Atomically (per process) check the cap and hold `amount_usd` for one hosted attempt."""
        async with self._lock:
            await self.check(db, amount_usd)
            row = BudgetReservation(
                learner_id=learner_id,
                request_id=request_id,
                registry_id=registry_id,
                task=task,
                amount_usd=round(amount_usd, 6),
                status="open",
                expires_at=(_now() + timedelta(seconds=RESERVATION_TTL_S)).isoformat(
                    timespec="milliseconds"
                ),
            )
            db.add(row)
            await db.commit()
            return row

    async def reconcile(
        self,
        db: AsyncSession,
        reservation: BudgetReservation,
        *,
        cost_usd: float,
        cost_status: str,
        model_call_id: str | None,
    ) -> None:
        """Settle a reservation against the logged call. Unknown billing settles at the reserved
        worst case (the model_call row carries `reserved_usd`, which is what the cap counts)."""
        reservation.status = "reconciled"
        reservation.settled_usd = (
            reservation.amount_usd if cost_status == "unknown" else round(cost_usd, 6)
        )
        reservation.model_call_id = model_call_id
        await db.commit()

    async def release(self, db: AsyncSession, reservation: BudgetReservation) -> None:
        """The provider was never reached (no adapter, spec error): nothing can have been billed."""
        reservation.status = "released"
        reservation.settled_usd = 0.0
        await db.commit()


def worst_case_usd(
    price_in_per_mtok: float,
    price_out_per_mtok: float,
    prompt_chars: int,
    max_tokens: int,
    n_messages: int,
) -> float:
    """Upper bound for one attempt: prompt chars / 3 (+ per-message overhead) in — a bound, not the
    chars/4 estimate — and `max_tokens` out (the output is bounded by `max_tokens`)."""
    tokens_in = prompt_chars // CHARS_PER_TOKEN_BOUND + 16 * max(n_messages, 1)
    return round(tokens_in / 1e6 * price_in_per_mtok + max_tokens / 1e6 * price_out_per_mtok, 6)
