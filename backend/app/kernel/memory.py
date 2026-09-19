"""MemoryState via FSRS (py-fsrs), per review item (ADR-0004). Only this module writes memory_state.

`now` is injectable everywhere so tests and benchmarks can time-travel ("review 2 days later").
"""

from datetime import UTC, datetime
from typing import Any, cast

from fsrs import Card, Rating, Scheduler
from fsrs.card import CardDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.events import EventWriter, Verb
from app.db.models import MemoryState, ReviewItem, ReviewLog
from app.schemas.common import ObjectType

DESIRED_RETENTION = 0.9
REVIEW_CAP_BY_MODE = {"low_capacity": 5, "steady": 10, "novelty": 15}


def scheduler() -> Scheduler:
    return Scheduler(desired_retention=DESIRED_RETENTION)


def review_cap(mode: str, energy: int) -> int:
    """Minimum-viable review: capped subset, smaller when energy is low."""
    base = REVIEW_CAP_BY_MODE.get(mode, 10)
    if energy <= 2:
        return min(base, 5)
    if energy == 3:
        return min(base, 10)
    return base


def rating_from_score(score: float, *, hint_count: int = 0) -> Rating:
    """Map a 0-1 grade to an FSRS rating; a hinted answer never counts as Easy."""
    if score < 0.5:
        return Rating.Again
    if score < 0.85:
        return Rating.Hard
    if score < 1.0 or hint_count > 0:
        return Rating.Good
    return Rating.Easy


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat(timespec="milliseconds")


def _state_name(card: Card) -> str:
    return {1: "learning", 2: "review", 3: "relearning"}.get(int(card.state), "new")


async def ensure_item(
    db: AsyncSession,
    learner_id: str,
    skill_id: str,
    item_type: str,
    prompt: dict[str, Any],
    *,
    object_id: str | None = None,
    now: datetime | None = None,
) -> tuple[ReviewItem, MemoryState]:
    """Find-or-create the review item for (learner, skill, item_type, prompt['ref']) and its card."""
    now = now or datetime.now(UTC)
    ref = prompt.get("ref")
    stmt = select(ReviewItem).where(
        ReviewItem.learner_id == learner_id,
        ReviewItem.skill_id == skill_id,
        ReviewItem.item_type == item_type,
    )
    item = next(
        (r for r in (await db.execute(stmt)).scalars() if r.prompt_json.get("ref") == ref), None
    )
    if item is None:
        item = ReviewItem(
            learner_id=learner_id,
            skill_id=skill_id,
            object_id=object_id,
            item_type=item_type,
            prompt_json=prompt,
        )
        db.add(item)
        await db.flush()
    ms = (
        await db.execute(select(MemoryState).where(MemoryState.review_item_id == item.id))
    ).scalar_one_or_none()
    if ms is None:
        card = Card(due=now)
        ms = MemoryState(
            learner_id=learner_id,
            review_item_id=item.id,
            fsrs_card_json=card.to_dict(),
            state="new",
            due=_iso(now),
        )
        db.add(ms)
    await db.commit()
    return item, ms


async def due_items(
    db: AsyncSession, learner_id: str, *, now: datetime | None = None, cap: int = 10
) -> list[tuple[ReviewItem, MemoryState]]:
    now = now or datetime.now(UTC)
    stmt = (
        select(ReviewItem, MemoryState)
        .join(MemoryState, MemoryState.review_item_id == ReviewItem.id)
        .where(
            ReviewItem.learner_id == learner_id,
            ReviewItem.active.is_(True),
            MemoryState.due <= _iso(now),
        )
        .order_by(MemoryState.due)
        .limit(cap)
    )
    return [(item, ms) for item, ms in (await db.execute(stmt)).all()]


async def review(
    db: AsyncSession,
    learner_id: str,
    review_item_id: str,
    rating: int,
    *,
    now: datetime | None = None,
    latency_ms: int | None = None,
    events: EventWriter | None = None,
) -> ReviewLog:
    now = now or datetime.now(UTC)
    ms = (
        await db.execute(
            select(MemoryState).where(
                MemoryState.review_item_id == review_item_id, MemoryState.learner_id == learner_id
            )
        )
    ).scalar_one()
    item = await db.get(ReviewItem, review_item_id)
    assert item is not None
    sched = scheduler()
    card = Card.from_dict(cast(CardDict, ms.fsrs_card_json))
    retrievability = float(sched.get_card_retrievability(card, now))
    stability_before = card.stability
    new_card, fsrs_log = sched.review_card(card, Rating(rating), review_datetime=now)
    ms.fsrs_card_json = dict(new_card.to_dict())
    ms.stability = new_card.stability
    ms.difficulty = new_card.difficulty
    ms.state = _state_name(new_card)
    ms.due = _iso(new_card.due)
    ms.last_review = _iso(now)
    days_since_learned = (
        (now - datetime.fromisoformat(item.created_at)).total_seconds() / 86400
        if item.created_at
        else 0.0
    )
    log = ReviewLog(
        learner_id=learner_id,
        review_item_id=review_item_id,
        rating=rating,
        reviewed_at=_iso(now),
        latency_ms=latency_ms,
        predicted_retrievability=retrievability,
        fsrs_log_json=fsrs_log.to_dict(),
    )
    db.add(log)
    await db.commit()
    if events is not None:
        await events.emit(
            Verb.REVIEWED,
            ObjectType.ITEM,
            review_item_id,
            result={
                "rating": rating,
                "latency_ms": latency_ms,
                "predicted_retrievability": round(retrievability, 4),
                "days_since_learned": round(days_since_learned, 3),
                "stability_before": stability_before,
                "stability_after": new_card.stability,
            },
            context={"item_type": item.item_type, "node_id": item.skill_id},
        )
    return log


async def mean_retrievability(
    db: AsyncSession, learner_id: str, skill_id: str, *, now: datetime | None = None
) -> float | None:
    now = now or datetime.now(UTC)
    stmt = (
        select(MemoryState)
        .join(ReviewItem, ReviewItem.id == MemoryState.review_item_id)
        .where(
            ReviewItem.learner_id == learner_id,
            ReviewItem.skill_id == skill_id,
            ReviewItem.active.is_(True),
        )
    )
    sched = scheduler()
    values = []
    for ms in (await db.execute(stmt)).scalars():
        if ms.last_review is None:
            continue  # never reviewed: no memory signal yet
        card = Card.from_dict(cast(CardDict, ms.fsrs_card_json))
        values.append(float(sched.get_card_retrievability(card, now)))
    return sum(values) / len(values) if values else None


async def skill_memory_summary(
    db: AsyncSession, learner_id: str, skill_id: str, *, now: datetime | None = None
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    stmt = (
        select(MemoryState)
        .join(ReviewItem, ReviewItem.id == MemoryState.review_item_id)
        .where(
            ReviewItem.learner_id == learner_id,
            ReviewItem.skill_id == skill_id,
            ReviewItem.active.is_(True),
        )
    )
    rows = list((await db.execute(stmt)).scalars())
    due = sum(1 for r in rows if r.due <= _iso(now))
    return {
        "items": len(rows),
        "due": due,
        "mean_retrievability": await mean_retrievability(db, learner_id, skill_id, now=now),
    }
