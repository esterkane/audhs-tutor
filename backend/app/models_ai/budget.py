"""In-app daily hosted budget (ADR-0001). Sums model_call.cost_usd since 00:00 UTC."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.traces import hosted_spend_since


class BudgetExceeded(Exception):
    def __init__(self, spent: float, cap: float) -> None:
        super().__init__(f"daily hosted budget exceeded: spent ${spent:.4f} of ${cap:.2f}")
        self.spent = spent
        self.cap = cap


def today_start_iso() -> str:
    now = datetime.now(UTC)
    return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat(timespec="milliseconds")


class Budget:
    def __init__(self, daily_cap_usd: float) -> None:
        self.daily_cap_usd = daily_cap_usd

    async def spent_today(self, db: AsyncSession) -> float:
        return await hosted_spend_since(db, today_start_iso())

    async def check(self, db: AsyncSession, projected_usd: float = 0.0) -> float:
        """Raise if today's spend (+ projected) would exceed the cap; return spend so far."""
        spent = await self.spent_today(db)
        if spent + projected_usd >= self.daily_cap_usd:
            raise BudgetExceeded(spent, self.daily_cap_usd)
        return spent
