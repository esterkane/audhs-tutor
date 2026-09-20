"""Whole-domain blocks (ADR-0006): language vocabulary on FSRS, guitar and movement practice.

Vocabulary cards are ordinary review items (`item_type="vocab"`) on a per-language skill node in
the LANGUAGE domain, so the same scheduler, cap and review log apply — but they only ever appear
in the language block (domain filters in `memory.due_items`). Practice blocks end with one
`practiced` event (duration, self-rating, activity); skipping is a `block_ended` with reason
"skipped", which the adaptation rules read. Nothing here calls a model."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.events import EventContext, EventWriter, Verb
from app.db.models import MemoryState, ReviewItem, Session, SkillNode
from app.kernel import memory
from app.schemas.common import ActivityType, Domain, Mode, ObjectType

PRACTICE_DOMAINS = ("guitar", "movement", "language")
ACTIVITIES: dict[str, list[str]] = {
    "movement": ["walk 5 minutes", "stretch", "stairs or squats"],
    "guitar": ["chord changes", "scale or picking pattern", "one song section"],
}

LANG_NAMES = {"de": "German", "en": "English", "es": "Spanish", "fr": "French", "it": "Italian"}


def deck_slug(lang: str) -> str:
    return f"lang-{lang.lower()}"


async def vocab_deck(db: AsyncSession, lang: str) -> SkillNode:
    """Get-or-create the language deck node (domain=language)."""
    slug = deck_slug(lang)
    node = (await db.execute(select(SkillNode).where(SkillNode.slug == slug))).scalar_one_or_none()
    if node is None:
        node = SkillNode(
            domain=str(Domain.LANGUAGE),
            slug=slug,
            title=f"{LANG_NAMES.get(lang.lower(), lang)} vocabulary",
            description="Spaced vocabulary deck",
            success_criteria_json=["recall the translation on a due card"],
        )
        db.add(node)
        await db.commit()
    return node


async def add_vocab(
    db: AsyncSession,
    learner_id: str,
    *,
    lang: str,
    word: str,
    translation: str,
    example: str | None = None,
    now: datetime | None = None,
) -> ReviewItem:
    node = await vocab_deck(db, lang)
    prompt: dict[str, Any] = {
        "ref": f"{lang.lower()}:{word.strip().casefold()}",
        "type": "vocab",
        "q": word.strip(),
        "a": translation.strip(),
        "lang": lang.lower(),
    }
    if example:
        prompt["example"] = example.strip()
    item, _ = await memory.ensure_item(db, learner_id, node.id, "vocab", prompt, now=now)
    return item


async def decks(
    db: AsyncSession, learner_id: str, *, now: datetime | None = None
) -> list[dict[str, Any]]:
    now = now or datetime.now(UTC)
    stmt = (
        select(
            SkillNode,
            func.count(ReviewItem.id),
            func.sum(case((MemoryState.due <= memory._iso(now), 1), else_=0)),
        )
        .join(ReviewItem, ReviewItem.skill_id == SkillNode.id)
        .join(MemoryState, MemoryState.review_item_id == ReviewItem.id)
        .where(SkillNode.domain == str(Domain.LANGUAGE), ReviewItem.learner_id == learner_id)
        .group_by(SkillNode.id)
    )
    return [
        {
            "lang": node.slug.removeprefix("lang-"),
            "title": node.title,
            "node_id": node.id,
            "cards": int(n),
            "due": int(due or 0),
        }
        for node, n, due in (await db.execute(stmt)).all()
    ]


async def language_due(db: AsyncSession, learner_id: str, *, now: datetime | None = None) -> int:
    return len(
        await memory.due_items(db, learner_id, now=now, cap=500, domain=str(Domain.LANGUAGE))
    )


async def log_practice(
    db: AsyncSession,
    learner_id: str,
    *,
    domain: str,
    activity: str,
    duration_min: float,
    self_rating: int,
    notes: str | None = None,
    session: Session | None = None,
) -> dict[str, Any]:
    if domain not in PRACTICE_DOMAINS:
        raise ValueError(f"domain must be one of {PRACTICE_DOMAINS}")
    if not 1 <= self_rating <= 5:
        raise ValueError("self_rating must be 1-5")
    if duration_min < 0:
        raise ValueError("duration_min must be ≥ 0")
    activity_type = ActivityType.MOVEMENT if domain == "movement" else ActivityType.DOMAIN_SWITCH
    if session is None:
        ctx = EventContext(
            learner_id=learner_id,
            session_id=None,
            mode=Mode.STEADY,
            energy=3,
            domain=Domain(domain),
            activity_type=activity_type,
        )
    else:
        ctx = EventContext(
            learner_id=learner_id,
            session_id=session.id,
            mode=Mode(session.mode),
            energy=session.energy,
            socratic=session.socratic,
            experiment_arm=session.experiment_arm_id,
            domain=Domain(domain),
            activity_type=activity_type,
        )
    ev = await EventWriter(db, ctx).emit(
        Verb.PRACTICED,
        ObjectType.BLOCK,
        session.id if session else "standalone",
        result={"duration_min": round(float(duration_min), 1), "self_rating": int(self_rating)},
        context={"domain": domain, "activity": activity, "notes": notes},
    )
    return {
        "event_id": ev.id,
        "domain": domain,
        "activity": activity,
        "duration_min": duration_min,
        "self_rating": self_rating,
    }
