"""Whole-domain blocks (ADR-0006): language vocabulary on FSRS, guitar and movement practice.

Vocabulary cards are ordinary review items (`item_type="vocab"`) on a per-language skill node in
the LANGUAGE domain, so the same scheduler, cap and review log apply — but they only ever appear
in the language block (domain filters in `memory.due_items`). Practice blocks end with one
`practiced` event (duration, self-rating, activity); skipping is a `block_ended` with reason
"skipped", which the adaptation rules read. Nothing here calls a model."""

import unicodedata
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

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
    return f"lang-{lang.strip().lower()}"


# a deck is reviewed on FSRS, never taught: keep it out of `next_skill` (P1 curriculum-eligibility)
DECK_REQUIREMENTS: dict[str, Any] = {"teachable": False, "kind": "vocab_deck"}


async def vocab_deck(db: AsyncSession, lang: str, *, commit: bool = True) -> SkillNode:
    """Get-or-create the language deck node (domain=language)."""
    slug = deck_slug(lang)
    node = (await db.execute(select(SkillNode).where(SkillNode.slug == slug))).scalar_one_or_none()
    if node is None:
        node = SkillNode(
            domain=str(Domain.LANGUAGE),
            slug=slug,
            title=f"{LANG_NAMES.get(lang.strip().lower(), lang.strip())} vocabulary",
            description="Spaced vocabulary deck",
            success_criteria_json=["recall the translation on a due card"],
            assessment_requirements_json=DECK_REQUIREMENTS,
        )
        db.add(node)
        await (db.commit() if commit else db.flush())
    elif (node.assessment_requirements_json or {}).get("teachable") is not False:
        node.assessment_requirements_json = {
            **(node.assessment_requirements_json or {}),
            **DECK_REQUIREMENTS,
        }
        await (db.commit() if commit else db.flush())  # rows created before P1 get the marker
    return node


def norm_text(text: str) -> str:
    """NFC-normalised, whitespace-collapsed, lower-cased. `lower()` (not `casefold()`) keeps
    `Maße` ≠ `Masse`; NFC makes a macOS-pasted (NFD) `é` equal to an NFC one."""
    return unicodedata.normalize("NFC", " ".join(text.split())).lower()


def _part(text: str) -> str:
    return quote(norm_text(text), safe="")  # ':' inside a word can never be read as a separator


def vocab_ref(lang: str, direction: str, word: str, meaning: str) -> str:
    """Card identity (P3): language + direction + normalised word + normalised meaning, so two
    meanings of one word are two cards and `Haus`/`haus ` are one."""
    return f"{lang.strip().lower()}:{direction}:{_part(word)}:{_part(meaning)}"


def legacy_vocab_ref(lang: str, word: str) -> str:
    return f"{lang.strip().lower()}:{norm_text(word)}"


@dataclass
class DeckIndex:
    """Cards of one deck keyed for O(1) identity checks (built once per bulk import)."""

    by_ref: dict[str, ReviewItem] = field(default_factory=dict)
    by_legacy: dict[str, list[ReviewItem]] = field(default_factory=dict)


async def deck_index(db: AsyncSession, learner_id: str, node_id: str) -> DeckIndex:
    idx = DeckIndex()
    stmt = select(ReviewItem).where(
        ReviewItem.learner_id == learner_id,
        ReviewItem.skill_id == node_id,
        ReviewItem.item_type == "vocab",
        ReviewItem.active.is_(True),
    )
    for item in (await db.execute(stmt)).scalars():
        ref = str(item.prompt_json.get("ref") or "")
        if item.prompt_json.get("direction") is None:  # pre-P3 card: `lang:word`
            idx.by_legacy.setdefault(ref, []).append(item)
        else:
            idx.by_ref[ref] = item
    return idx


async def add_vocab(
    db: AsyncSession,
    learner_id: str,
    *,
    lang: str,
    word: str,
    translation: str,
    example: str | None = None,
    direction: str = "forward",
    attribution: dict[str, Any] | None = None,
    now: datetime | None = None,
    commit: bool = True,
    index: DeckIndex | None = None,
) -> tuple[ReviewItem, bool]:
    """Find-or-create a card. Update policy: an existing card (same identity) keeps its id and FSRS
    schedule; only a missing `example`/attribution is filled in. A card still carrying the legacy
    `lang:word` ref is adopted when its stored meaning matches (ref rewritten in place, schedule
    kept). `index` (from `deck_index`) makes bulk imports O(1) per row. Returns (item, created)."""
    if direction not in ("forward", "reverse"):
        raise ValueError("direction must be forward or reverse")
    lang = lang.strip().lower()
    node = await vocab_deck(db, lang, commit=commit)
    word, translation = word.strip(), translation.strip()
    ref = vocab_ref(lang, direction, word, translation)
    idx = index if index is not None else await deck_index(db, learner_id, node.id)
    existing = idx.by_ref.get(ref)
    if existing is None and direction == "forward":
        for item in idx.by_legacy.get(legacy_vocab_ref(lang, word), []):
            if norm_text(str(item.prompt_json.get("a") or "")) == norm_text(translation):
                existing = item  # pre-P3 card: adopt it under the new identity
                break
    if existing is not None:
        prompt = dict(existing.prompt_json)
        changed = False
        if prompt.get("ref") != ref or prompt.get("direction") is None:
            prompt.update({"ref": ref, "direction": direction, "lang": lang})
            changed = True
            idx.by_ref[ref] = existing
        if example and not prompt.get("example"):
            prompt["example"] = example.strip()
            changed = True
        if attribution and not prompt.get("source"):
            prompt.update(attribution)
            changed = True
        if changed:
            existing.prompt_json = prompt
            if commit:
                await db.commit()
            else:
                await db.flush()
        return existing, False
    prompt = {
        "ref": ref,
        "type": "vocab",
        "q": word,
        "a": translation,
        "lang": lang,
        "direction": direction,
    }
    if example:
        prompt["example"] = example.strip()
    if attribution:
        prompt.update(attribution)
    item, _ = await memory.ensure_item(
        db, learner_id, node.id, "vocab", prompt, now=now, commit=commit, lookup=False
    )
    idx.by_ref[ref] = item
    return item, True


async def card_due(db: AsyncSession, item_id: str) -> str:
    ms = (
        await db.execute(select(MemoryState.due).where(MemoryState.review_item_id == item_id))
    ).scalar_one()
    return str(ms)


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
