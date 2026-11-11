"""Opt-in ungraded delayed recall of an immutable, authored reading question."""

from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select, text

from app.api.deps import DB, Learner
from app.core.errors import AppError
from app.db.base import utcnow_iso
from app.db.models import ReadingPrediction
from app.kernel import curriculum, knowledge_authoring, skill_graph
from app.kernel.content_access import shared_nodes_by_slug
from app.kernel.learning_scope import created_visible, reference_before, require_current_material

router = APIRouter(prefix="/reading-predictions", tags=["reading-predictions"])
QuestionId = Annotated[str, Field(pattern="^[0-9a-f]{64}$")]
ResponseText = Annotated[str, Field(min_length=1, max_length=4000)]


class EnrollPrediction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    draft_id: str = Field(min_length=1, max_length=64)
    learning_object_version: int = Field(ge=1)
    question_id: QuestionId
    prediction: ResponseText

    @field_validator("prediction")
    @classmethod
    def meaningful(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Enter a prediction.")
        return value


class RecallInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: ResponseText

    @field_validator("answer")
    @classmethod
    def meaningful(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Enter a recall answer.")
        return value


class PredictionReceipt(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    due_at: str


class DuePrediction(PredictionReceipt):
    question: str
    title: str


class CompletedRecall(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    question: str
    title: str
    prediction: str
    answer: str
    passage: str
    created_at: str
    answered_at: str


async def existing(
    db: DB, owner: str, draft: str, version: int, question: str
) -> ReadingPrediction | None:
    row: ReadingPrediction | None = await db.scalar(
        select(ReadingPrediction).where(
            ReadingPrediction.learner_id == owner,
            ReadingPrediction.draft_id == draft,
            ReadingPrediction.learning_object_version == version,
            ReadingPrediction.question_id == question,
        )
    )
    return row


@router.get("/enrollment", response_model=PredictionReceipt | None)
async def enrollment(
    draft_id: str, learning_object_version: int, question_id: QuestionId, db: DB, learner: Learner
) -> PredictionReceipt | None:
    row = await existing(db, learner.id, draft_id, learning_object_version, question_id)
    cutoff = await reference_before(db, learner.id)
    if row is None or (cutoff is not None and row.created_at <= cutoff):
        return None
    return PredictionReceipt.model_validate(row)


@router.post("", response_model=PredictionReceipt)
async def enroll(body: EnrollPrediction, db: DB, learner: Learner) -> PredictionReceipt:
    await db.commit()
    await db.execute(text("BEGIN IMMEDIATE"))
    row = await existing(
        db, learner.id, body.draft_id, body.learning_object_version, body.question_id
    )
    if row is not None:
        await require_current_material(db, learner.id, row.created_at)
        if row.prediction != body.prediction:
            raise AppError(
                "prediction_already_saved",
                "A different prediction is already saved for this reading question.",
                409,
            )
        return PredictionReceipt.model_validate(row)
    draft = await curriculum.get_draft(db, learner.id, body.draft_id)
    await require_current_material(db, learner.id, draft.created_at)
    skills = draft.payload_json.get("skills") or []
    if draft.origin != "knowledge_authored" or draft.status != "published" or len(skills) != 1:
        raise AppError(
            "prediction_source_changed", "Open the accepted lesson and its authored question.", 409
        )
    slug = skills[0]["slug"]
    latest = await curriculum.latest_accepted_material(db, learner.id, slug)
    node = (await shared_nodes_by_slug(db, [slug])).get(slug)
    obj = (
        await skill_graph.learning_object_for(db, node.id, learner_id=learner.id) if node else None
    )
    if (
        latest is None
        or latest.id != draft.id
        or obj is None
        or obj.version != body.learning_object_version
    ):
        raise AppError(
            "prediction_source_changed", "The lesson has changed. Open its accepted version.", 409
        )
    examples = [*obj.examples_json, "", ""]
    questions = knowledge_authoring.accepted_prequestions(
        draft.payload_json.get("authoring", {}), examples[0], examples[1]
    )
    question = next((q for q in questions if q.question_id == body.question_id), None)
    if question is None:
        raise AppError(
            "prediction_question_changed",
            "This authored question is unavailable in the accepted lesson.",
            409,
        )
    now = utcnow_iso()
    row = ReadingPrediction(
        learner_id=learner.id,
        draft_id=draft.id,
        object_id=obj.id,
        learning_object_version=obj.version,
        question_id=question.question_id,
        target=question.target,
        content_sha256=question.content_sha256,
        title=node.title if node else obj.concept,
        question=question.question,
        passage=examples[0 if question.target == "explanation" else 1],
        prediction=body.prediction,
        created_at=now,
        due_at=(datetime.fromisoformat(now) + timedelta(days=1)).isoformat(timespec="milliseconds"),
    )
    db.add(row)
    await db.commit()
    return PredictionReceipt.model_validate(row)


@router.get("/due", response_model=DuePrediction | None)
async def due(db: DB, learner: Learner) -> DuePrediction | None:
    row = await db.scalar(
        select(ReadingPrediction)
        .where(
            ReadingPrediction.learner_id == learner.id,
            ReadingPrediction.answered_at.is_(None),
            ReadingPrediction.due_at <= utcnow_iso(),
            created_visible(learner.id, ReadingPrediction.created_at),
        )
        .order_by(ReadingPrediction.due_at, ReadingPrediction.id)
        .limit(1)
    )
    return DuePrediction.model_validate(row) if row else None


@router.get("/latest-recall", response_model=CompletedRecall | None)
async def latest_recall(db: DB, learner: Learner) -> CompletedRecall | None:
    row = await db.scalar(
        select(ReadingPrediction)
        .where(
            ReadingPrediction.learner_id == learner.id,
            ReadingPrediction.answered_at.is_not(None),
            created_visible(learner.id, ReadingPrediction.created_at),
        )
        .order_by(ReadingPrediction.answered_at.desc(), ReadingPrediction.id.desc())
        .limit(1)
    )
    return CompletedRecall.model_validate(row) if row else None


@router.post("/{prediction_id}/recall", response_model=CompletedRecall)
async def recall(
    prediction_id: str, body: RecallInput, db: DB, learner: Learner
) -> CompletedRecall:
    await db.commit()
    await db.execute(text("BEGIN IMMEDIATE"))
    row = await db.get(ReadingPrediction, prediction_id)
    if row is None or row.learner_id != learner.id:
        raise AppError("not_found", "This reading prediction is unavailable.", 404)
    await require_current_material(db, learner.id, row.created_at)
    if row.answer is not None:
        if row.answer != body.answer:
            raise AppError(
                "recall_already_saved", "A different recall answer is already saved.", 409
            )
    else:
        now = utcnow_iso()
        if row.due_at > now:
            raise AppError(
                "recall_not_due", "This prediction is not yet due for delayed recall.", 409
            )
        row.answer = body.answer
        row.answered_at = now
        await db.commit()
    return CompletedRecall.model_validate(row)
