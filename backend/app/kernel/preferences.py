"""Structured learner preferences (never free-text chat memory). Keys are a closed registry with types
and defaults; `origin` records who decided (explicit | proposed_accepted | inferred)."""

from typing import Any

from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.events import EventWriter, Verb
from app.db.models import LearnerPreference
from app.schemas.common import ObjectType


class PrefSpec(BaseModel):
    key: str
    type: str  # bool | int | str | enum
    default: Any
    choices: list[str] | None = None
    min: int | None = None
    max: int | None = None
    description: str


PREFERENCES: dict[str, PrefSpec] = {
    p.key: p
    for p in [
        PrefSpec(
            key="session.default_mode",
            type="enum",
            default="steady",
            choices=["novelty", "steady", "low_capacity"],
            description="Preselected state mode on Home",
        ),
        PrefSpec(
            key="session.socratic_default",
            type="bool",
            default=False,
            description="Preselect Socratic questioning",
        ),
        PrefSpec(
            key="tutor.representation_default",
            type="enum",
            default="",
            choices=["", "analogy", "derivation", "code", "diagram", "worked_example", "narrative"],
            description="Preferred first representation",
        ),
        PrefSpec(
            key="planner.new_material_min",
            type="int",
            default=20,
            min=5,
            max=45,
            description="Planned minutes for new material",
        ),
        PrefSpec(
            key="planner.review_min",
            type="int",
            default=10,
            min=3,
            max=30,
            description="Planned minutes for interleaved review",
        ),
        PrefSpec(
            key="planner.movement",
            type="enum",
            default="before",
            choices=["before", "after", "off"],
            description="Movement primer placement relative to new material",
        ),
        PrefSpec(
            key="planner.language",
            type="bool",
            default=False,
            description="Plan a language (vocabulary) block when cards are due",
        ),
        PrefSpec(
            key="goal.course",
            type="str",
            default="",
            description="Learn toward this course's published skills first (empty = whole map)",
        ),
        PrefSpec(
            key="voice.enabled",
            type="bool",
            default=False,
            description="Voice: talk to the tutor (activated by you after setup and a test)",
        ),
        PrefSpec(
            key="voice.retain_audio",
            type="bool",
            default=False,
            description="Voice: keep my recordings (off = deleted right after transcription)",
        ),
        PrefSpec(
            key="voice.retention_days",
            type="int",
            default=7,
            min=1,
            max=90,
            description="Voice: days to keep recordings when retention is on",
        ),
        PrefSpec(
            key="voice.conversation_lang",
            type="str",
            default="",
            description="Voice: language for spoken conversation practice in the language block "
            "(ISO code, e.g. de; empty = no conversation option)",
        ),
        PrefSpec(
            key="voice.voice",
            type="str",
            default="af_heart",
            description="Voice: Kokoro voice id",
        ),
        PrefSpec(
            key="voice.early_speech",
            type="bool",
            default=True,
            description="Voice: start speaking at the first clause of an answer (faster first "
            "audio; the rest of the sentence follows after a short seam). Off = whole sentences",
        ),
        PrefSpec(
            key="listening.document_id",
            type="str",
            default="",
            description="The listening lesson offered in the language block (empty = none)",
        ),
        PrefSpec(
            key="planner.guitar",
            type="bool",
            default=False,
            description="Plan a guitar practice block at a boundary",
        ),
        PrefSpec(
            key="planner.challenge",
            type="bool",
            default=True,
            description="Include a critical-thinking challenge block when energy allows",
        ),
        PrefSpec(
            key="ui.reduced_motion", type="bool", default=True, description="No motion in the UI"
        ),
        PrefSpec(
            key="ui.density",
            type="enum",
            default="comfortable",
            choices=["compact", "comfortable"],
            description="Screen density",
        ),
        PrefSpec(key="ui.sound", type="bool", default=False, description="UI sounds"),
        PrefSpec(
            key="ui.theme",
            type="enum",
            default="system",
            choices=["system", "light", "dark"],
            description="Colour theme",
        ),
        PrefSpec(
            key="ui.font_scale",
            type="enum",
            default="normal",
            choices=["normal", "large"],
            description="Text size",
        ),
        PrefSpec(
            key="ui.notifications",
            type="bool",
            default=False,
            description="Browser notifications for wind-down prompts",
        ),
        PrefSpec(
            key="ui.ambient",
            type="enum",
            default="off",
            choices=["off", "brown_noise"],
            description="Ambient sound on the body-doubling screen (opt-in, never autoplays)",
        ),
    ]
}

ORIGINS = ("explicit", "proposed_accepted", "inferred")


def validate(key: str, value: Any) -> Any:
    spec = PREFERENCES.get(key)
    if spec is None:
        raise ValueError(f"unknown preference {key!r}")
    if spec.type == "bool":
        if not isinstance(value, bool):
            raise ValueError(f"{key} must be a boolean")
    elif spec.type == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{key} must be an integer")
        if spec.min is not None and value < spec.min or spec.max is not None and value > spec.max:
            raise ValueError(f"{key} must be between {spec.min} and {spec.max}")
    elif spec.type == "enum":
        if not isinstance(value, str) or value not in (spec.choices or []):
            raise ValueError(f"{key} must be one of {spec.choices}")
    return value


async def get_all(db: AsyncSession, learner_id: str) -> dict[str, Any]:
    stmt = select(LearnerPreference).where(LearnerPreference.learner_id == learner_id)
    stored = {
        p.key: p.value_json for p in (await db.execute(stmt)).scalars() if p.key in PREFERENCES
    }
    return {k: stored.get(k, spec.default) for k, spec in PREFERENCES.items()}


async def get(db: AsyncSession, learner_id: str, key: str) -> Any:
    return (await get_all(db, learner_id)).get(key, PREFERENCES[key].default)


async def set_pref(
    db: AsyncSession,
    learner_id: str,
    key: str,
    value: Any,
    *,
    origin: str = "explicit",
    confidence: float = 1.0,
    reversible: bool = True,
    events: EventWriter | None = None,
    event_object_id: str | None = None,
    policy_version: str = "v1",
) -> LearnerPreference:
    validate(key, value)
    if origin not in ORIGINS:
        raise ValueError(f"origin must be one of {ORIGINS}")
    stmt = select(LearnerPreference).where(
        LearnerPreference.learner_id == learner_id, LearnerPreference.key == key
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        row = LearnerPreference(
            learner_id=learner_id,
            key=key,
            value_json=value,
            origin=origin,
            confidence=confidence,
            reversible=reversible,
        )
        db.add(row)
    else:
        row.value_json, row.origin, row.confidence, row.reversible = (
            value,
            origin,
            confidence,
            reversible,
        )
    await db.commit()
    if events is not None and origin != "explicit":
        await events.emit(
            Verb.ADAPTED,
            ObjectType.ADAPTATION,
            event_object_id or key,
            context={
                "what": f"{key}={value}",
                "why": origin,
                "reversible": reversible,
                "policy_version": policy_version,
            },
        )
    return row


async def is_set(db: AsyncSession, learner_id: str, key: str) -> bool:
    stmt = select(LearnerPreference.id).where(
        LearnerPreference.learner_id == learner_id, LearnerPreference.key == key
    )
    return (await db.execute(stmt)).scalar_one_or_none() is not None


async def reset(db: AsyncSession, learner_id: str, key: str) -> None:
    if key not in PREFERENCES:
        raise KeyError(f"unknown preference {key!r}")
    await db.execute(
        delete(LearnerPreference).where(
            LearnerPreference.learner_id == learner_id, LearnerPreference.key == key
        )
    )
    await db.commit()
