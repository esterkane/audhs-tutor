"""P6 cost view: what was spent, on what, with which confidence — from `model_call` rows only.

Statuses are never merged into one number without saying so: `reported` (provider price),
`estimated` (tokens × registry price, or chars/4 for streams without a final usage chunk),
`unknown` (failed hosted call with no usage — counted at the reserved worst case), `legacy` (rows
written before P6: tokens may be estimates, cost by registry price; not re-labelled), `free` (local).
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BudgetReservation, ModelCall
from app.models_ai.budget import Budget, Spend
from app.models_ai.provider import HOSTED_PROVIDERS


@dataclass
class Breakdown:
    key: str
    calls: int = 0
    failed: int = 0
    cost_usd: float = 0.0
    unknown_usd: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0


@dataclass
class Failure:
    ts: str
    request_id: str | None
    attempt: int
    registry_id: str
    task: str
    route: str
    outcome: str
    cost_status: str
    reserved_usd: float
    error: str | None


@dataclass
class CostReport:
    day_start: str
    window_start: str
    spend: Spend
    hosted_calls: int = 0
    free_calls: int = 0
    failed_calls: int = 0
    cancelled_calls: int = 0
    blocked_calls: int = 0
    retried_requests: int = 0
    legacy_rows: int = 0
    unknown_calls: int = 0
    by_task: list[Breakdown] = field(default_factory=list)
    by_provider: list[Breakdown] = field(default_factory=list)
    recent_failures: list[Failure] = field(default_factory=list)
    open_reservations: int = 0
    expired_reservations: int = 0


def _since(days: int) -> str:
    now = datetime.now(UTC)
    start = (now - timedelta(days=max(days, 1) - 1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return start.isoformat(timespec="milliseconds")


async def cost_report(db: AsyncSession, budget: Budget, *, days: int = 1) -> CostReport:
    since = _since(days)
    spend = await budget.spend_today(db)
    rep = CostReport(day_start=_since(1), window_start=since, spend=spend)
    rows = (await db.execute(select(ModelCall).where(ModelCall.ts >= since))).scalars().all()
    tasks: dict[str, Breakdown] = {}
    providers: dict[str, Breakdown] = {}
    requests_attempts: dict[str, int] = {}
    for r in rows:
        hosted = r.provider in HOSTED_PROVIDERS
        if hosted:
            rep.hosted_calls += 1
        else:
            rep.free_calls += 1
        if r.outcome == "blocked":
            rep.blocked_calls += 1
        elif r.outcome == "cancelled":
            rep.cancelled_calls += 1  # the learner stopped it: not a failure
        elif not r.ok:
            rep.failed_calls += 1
        if r.usage_source == "legacy":
            rep.legacy_rows += 1
        if r.cost_status == "unknown":
            rep.unknown_calls += 1
        if r.request_id:
            requests_attempts[r.request_id] = max(requests_attempts.get(r.request_id, 0), r.attempt)
        for bucket, key in ((tasks, r.task), (providers, r.provider)):
            b = bucket.setdefault(key, Breakdown(key=key))
            b.calls += 1
            b.failed += 0 if r.ok else 1
            b.tokens_in += r.tokens_in
            b.tokens_out += r.tokens_out
            if r.cost_status in ("reported", "estimated", "legacy"):
                b.cost_usd = round(b.cost_usd + r.cost_usd, 6)
            elif r.cost_status == "unknown":
                b.unknown_usd = round(b.unknown_usd + r.reserved_usd, 6)
    rep.retried_requests = sum(1 for n in requests_attempts.values() if n > 1)
    rep.by_task = sorted(tasks.values(), key=lambda b: (-b.cost_usd, -b.calls, b.key))
    rep.by_provider = sorted(providers.values(), key=lambda b: (-b.cost_usd, b.key))
    failures = (
        await db.execute(
            select(ModelCall)
            .where(ModelCall.ts >= since, ModelCall.ok.is_(False))
            .order_by(ModelCall.ts.desc())
            .limit(30)
        )
    ).scalars()
    rep.recent_failures = [
        Failure(
            ts=r.ts,
            request_id=r.request_id,
            attempt=r.attempt,
            registry_id=r.registry_id,
            task=r.task,
            route=r.route,
            outcome=r.outcome,
            cost_status=r.cost_status,
            reserved_usd=r.reserved_usd,
            error=(r.error or "")[:200] or None,
        )
        for r in failures
    ]
    counts = (
        await db.execute(
            select(BudgetReservation.status, func.count(BudgetReservation.id))
            .where(BudgetReservation.created_at >= since)
            .group_by(BudgetReservation.status)
        )
    ).all()
    for status, n in counts:
        if status == "open":
            rep.open_reservations = int(n)
        elif status == "expired":
            rep.expired_reservations = int(n)
    return rep


def report_dict(rep: CostReport) -> dict[str, Any]:
    s = rep.spend
    return {
        "daily_cap_usd": s.cap,
        "day_start": rep.day_start,
        "window_start": rep.window_start,
        "today": {
            "counted": s.counted,
            "remaining": s.remaining,
            "reported": round(s.reported, 6),
            "estimated": round(s.estimated, 6),
            "unknown_reserved": round(s.unknown_reserved, 6),
            "legacy": round(s.legacy, 6),
            "open_reservations": round(s.open_reservations, 6),
        },
        "window": {
            "hosted_calls": rep.hosted_calls,
            "free_calls": rep.free_calls,
            "failed_calls": rep.failed_calls,
            "cancelled_calls": rep.cancelled_calls,
            "blocked_calls": rep.blocked_calls,
            "retried_requests": rep.retried_requests,
            "unknown_calls": rep.unknown_calls,
            "legacy_rows": rep.legacy_rows,
            "open_reservations": rep.open_reservations,
            "expired_reservations": rep.expired_reservations,
        },
        "by_task": [b.__dict__ for b in rep.by_task],
        "by_provider": [b.__dict__ for b in rep.by_provider],
        "recent_failures": [f.__dict__ for f in rep.recent_failures],
    }
