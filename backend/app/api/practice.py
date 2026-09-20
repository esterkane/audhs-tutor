"""Practice blocks (movement / guitar) and vocabulary decks (language). Whole blocks, ADR-0006."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import DB, Learner
from app.kernel import practice
from app.kernel import session as ksession

router = APIRouter(tags=["practice"])


class PracticeIn(BaseModel):
    session_id: str | None = None
    domain: str
    activity: str = Field(min_length=1, max_length=120)
    duration_min: float = Field(ge=0, le=180)
    self_rating: int = Field(ge=1, le=5)
    notes: str | None = Field(default=None, max_length=500)


class PracticeOut(BaseModel):
    event_id: str
    domain: str
    activity: str
    duration_min: float
    self_rating: int


class ActivitiesOut(BaseModel):
    activities: dict[str, list[str]]


@router.post(
    "/practice",
    summary="Log a practice block (movement / guitar / language) as a practiced event",
    response_model=PracticeOut,
)
async def log(body: PracticeIn, db: DB, learner: Learner) -> PracticeOut:
    session = await ksession.get(db, body.session_id) if body.session_id else None
    out = await practice.log_practice(
        db,
        learner.id,
        domain=body.domain,
        activity=body.activity,
        duration_min=body.duration_min,
        self_rating=body.self_rating,
        notes=body.notes,
        session=session,
    )
    return PracticeOut(**out)


@router.get(
    "/practice/activities",
    summary="Concrete activity options per domain (2–3 choices)",
    response_model=ActivitiesOut,
)
async def activities() -> ActivitiesOut:
    return ActivitiesOut(activities=practice.ACTIVITIES)


class VocabIn(BaseModel):
    lang: str = Field(min_length=2, max_length=8)
    word: str = Field(min_length=1, max_length=120)
    translation: str = Field(min_length=1, max_length=200)
    example: str | None = Field(default=None, max_length=300)


class VocabItemOut(BaseModel):
    item_id: str
    lang: str
    word: str
    translation: str
    due: str


class DeckList(BaseModel):
    decks: list[dict[str, Any]]
    due_total: int


@router.get("/vocab", summary="Vocabulary decks with card and due counts", response_model=DeckList)
async def decks(db: DB, learner: Learner) -> DeckList:
    d = await practice.decks(db, learner.id)
    return DeckList(decks=d, due_total=sum(int(x["due"]) for x in d))


@router.post(
    "/vocab",
    summary="Add a vocabulary card (FSRS-scheduled, reviewed in the language block)",
    response_model=VocabItemOut,
    status_code=201,
)
async def add(body: VocabIn, db: DB, learner: Learner) -> VocabItemOut:
    item = await practice.add_vocab(
        db,
        learner.id,
        lang=body.lang,
        word=body.word,
        translation=body.translation,
        example=body.example,
    )
    from sqlalchemy import select

    from app.db.models import MemoryState

    ms = (
        await db.execute(select(MemoryState).where(MemoryState.review_item_id == item.id))
    ).scalar_one()
    return VocabItemOut(
        item_id=item.id,
        lang=body.lang.lower(),
        word=item.prompt_json["q"],
        translation=item.prompt_json["a"],
        due=ms.due,
    )
