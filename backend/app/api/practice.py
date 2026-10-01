"""Practice blocks (movement / guitar) and vocabulary decks (language). Whole blocks, ADR-0006."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import DB, Learner
from app.core.errors import AppError
from app.kernel import practice, vocab_import
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


LANG = r"^[A-Za-z]{2,3}(-[A-Za-z]{2,4})?$"


class VocabIn(BaseModel):
    lang: str = Field(pattern=LANG)
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
    item, _created = await practice.add_vocab(
        db,
        learner.id,
        lang=body.lang,
        word=body.word,
        translation=body.translation,
        example=body.example,
    )
    return VocabItemOut(
        item_id=item.id,
        lang=body.lang.lower(),
        word=body.word,
        translation=body.translation,
        due=await practice.card_due(db, item.id),
    )


# ----------------------------------------------------------------------------- CSV import (P3)
class ImportPreviewIn(BaseModel):
    lang: str = Field(min_length=2, max_length=8)
    csv_text: str = Field(
        max_length=2_000_000, description="file contents (the browser reads the file)"
    )
    reverse: bool = False


class PreviewRowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    row: int
    word: str
    translation: str
    example: str | None
    status: str
    problem: str | None = None


class ImportPreviewOut(BaseModel):
    lang: str
    rows: list[PreviewRowOut]
    columns: dict[str, int]
    delimiter: str
    header: bool
    counts: dict[str, int]
    errors: list[str]


class ImportRowIn(BaseModel):
    word: str = Field(max_length=vocab_import.MAX_WORD)
    translation: str = Field(max_length=vocab_import.MAX_MEANING)
    example: str | None = Field(default=None, max_length=vocab_import.MAX_EXAMPLE)


class ImportIn(BaseModel):
    lang: str = Field(pattern=LANG)
    rows: list[ImportRowIn] = Field(max_length=2000)
    reverse: bool = Field(default=False, description="also create the translation → word card")
    source: str | None = Field(
        default=None, max_length=200, description="file name for attribution"
    )


class ImportOut(BaseModel):
    lang: str
    added: int
    reverse_added: int
    reverse_skipped: int = 0
    skipped_existing: int
    duplicate_in_file: int = 0
    invalid: int


@router.post(
    "/vocab/import/preview",
    summary="Parse a CSV vocabulary list: detected columns, one status per row, nothing saved",
    response_model=ImportPreviewOut,
)
async def import_preview(body: ImportPreviewIn, db: DB, learner: Learner) -> ImportPreviewOut:
    data = body.csv_text.encode("utf-8")
    if len(data) > vocab_import.MAX_BYTES:
        raise AppError("too_large", "CSV text larger than 2 MB", http_status=413)
    pv = await vocab_import.preview(db, learner.id, lang=body.lang, data=data, reverse=body.reverse)
    return ImportPreviewOut(
        lang=body.lang.lower(),
        rows=[PreviewRowOut.model_validate(r, from_attributes=True) for r in pv.rows],
        columns=pv.columns,
        delimiter=pv.delimiter,
        header=pv.header,
        counts=pv.counts,
        errors=pv.errors,
    )


@router.post(
    "/vocab/import",
    summary="Import the confirmed rows as FSRS cards (idempotent; existing schedules untouched)",
    response_model=ImportOut,
    status_code=201,
)
async def import_cards(body: ImportIn, db: DB, learner: Learner) -> ImportOut:
    res = await vocab_import.import_rows(
        db,
        learner.id,
        lang=body.lang,
        rows=[r.model_dump() for r in body.rows],
        reverse=body.reverse,
        source=body.source,
    )
    return ImportOut(
        lang=res.lang,
        added=res.added,
        reverse_added=res.reverse_added,
        reverse_skipped=res.reverse_skipped,
        skipped_existing=res.skipped_existing,
        duplicate_in_file=res.duplicate_in_file,
        invalid=res.invalid,
    )
