from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.api.deps import DB, Learner
from app.db.models import Assessment, SkillNode
from app.kernel import memory
from app.kernel import session as ksession
from app.orchestrator.grader import view

router = APIRouter(prefix="/review", tags=["review"])


class ReviewItemOut(BaseModel):
    item_id: str
    skill_id: str
    skill_title: str
    item_type: str
    question: str
    options: list[str] | None
    reveal: str
    due: str
    state: str


class DueList(BaseModel):
    items: list[ReviewItemOut]
    cap: int
    total_due: int
    as_of: str


class ReviewRating(BaseModel):
    session_id: str
    rating: int = Field(ge=1, le=4)
    latency_ms: int | None = None


class ReviewOut(BaseModel):
    item_id: str
    due: str
    state: str
    stability: float | None
    predicted_retrievability: float | None


def _as_of(value: str | None) -> datetime:
    return datetime.fromisoformat(value) if value else datetime.now(UTC)


async def _reveal(db: DB, prompt: dict[str, Any]) -> tuple[str, list[str] | None, str]:
    a = await db.get(Assessment, str(prompt.get("assessment_id") or prompt.get("ref")))
    if a is None:
        return str(prompt.get("q", "")), None, ""
    v = view(a)
    item = a.item_json
    if a.kind == "mcq":
        reveal = f"{item['options'][int(item['answer'])]} — {item.get('explanation', '')}".strip(
            " —"
        )
    elif a.kind == "cloze":
        reveal = str(item["answers"][0])
    else:
        rubric = (
            await db.get(
                __import__("app.db.models", fromlist=["AssessmentRubric"]).AssessmentRubric,
                a.rubric_id,
            )
            if a.rubric_id
            else None
        )
        reveal = "A complete answer covers: " + "; ".join(
            c["criterion"] for c in (rubric.criteria_json if rubric else [])
        )
    return v.question, v.options, reveal


@router.get(
    "/due",
    summary="Due review items, capped to the minimum-viable review for this session",
    response_model=DueList,
)
async def due(
    db: DB,
    learner: Learner,
    session_id: str = Query(...),
    as_of: str | None = Query(None, description="ISO time; dev/benchmark time travel"),
) -> DueList:
    s = await ksession.get(db, session_id)
    now = _as_of(as_of)
    cap = memory.review_cap(s.mode, s.energy)
    all_due = await memory.due_items(db, learner.id, now=now, cap=500)
    items = []
    for item, ms in all_due[:cap]:
        node = await db.get(SkillNode, item.skill_id)
        question, options, reveal = await _reveal(db, item.prompt_json)
        items.append(
            ReviewItemOut(
                item_id=item.id,
                skill_id=item.skill_id,
                skill_title=node.title if node else "",
                item_type=item.item_type,
                question=question,
                options=options,
                reveal=reveal,
                due=ms.due,
                state=ms.state,
            )
        )
    return DueList(items=items, cap=cap, total_due=len(all_due), as_of=now.isoformat())


@router.post("/{item_id}", summary="Rate a recalled item 1-4 (FSRS)", response_model=ReviewOut)
async def rate(
    item_id: str, body: ReviewRating, db: DB, learner: Learner, as_of: str | None = Query(None)
) -> ReviewOut:
    s = await ksession.get(db, body.session_id)
    from app.db.events import EventWriter
    from app.schemas.common import ActivityType

    events = EventWriter(db, ksession.event_context(s, activity=ActivityType.RETRIEVAL))
    log = await memory.review(
        db,
        learner.id,
        item_id,
        body.rating,
        now=_as_of(as_of),
        latency_ms=body.latency_ms,
        events=events,
    )
    from sqlalchemy import select

    from app.db.models import MemoryState

    ms = (
        await db.execute(select(MemoryState).where(MemoryState.review_item_id == item_id))
    ).scalar_one()
    return ReviewOut(
        item_id=item_id,
        due=ms.due,
        state=ms.state,
        stability=ms.stability,
        predicted_retrievability=log.predicted_retrievability,
    )
