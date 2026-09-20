from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.api.deps import DB, Learner
from app.db.events import EventWriter, Verb
from app.db.models import Assessment, SkillNode
from app.kernel import memory
from app.kernel import session as ksession
from app.orchestrator.grader import view
from app.schemas.common import ActivityType, Actor, ObjectType

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
    confidence_pre: int | None = Field(default=None, ge=1, le=5)
    latency_ms: int | None = None


class ReviewOut(BaseModel):
    item_id: str
    due: str
    state: str
    stability: float | None
    predicted_retrievability: float | None


def _as_of(value: str | None) -> datetime:
    """Dev/benchmark time travel. Must carry a timezone; naive stamps would corrupt FSRS state."""
    if not value:
        return datetime.now(UTC)
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError("as_of must include a timezone offset, e.g. 2030-01-01T00:00:00+00:00")
    return dt


async def _reveal(db: DB, prompt: dict[str, Any]) -> tuple[str, list[str] | None, str]:
    if prompt.get("type") == "vocab":
        example = f" — e.g. {prompt['example']}" if prompt.get("example") else ""
        return str(prompt.get("q", "")), None, f"{prompt.get('a', '')}{example}"
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
    all: bool = Query(False, description="Undo the minimum-viable cap for this call"),
    domain: str | None = Query(
        None, description="only this domain (e.g. language); default: all but language"
    ),
) -> DueList:
    s = await ksession.get(db, session_id)
    now = _as_of(as_of)
    cap = memory.review_cap(s.mode, s.energy)
    all_due = await memory.due_items(
        db,
        learner.id,
        now=now,
        cap=500,
        domain=domain,
        exclude_domains=() if domain else ("language",),  # AI/ML review never mixes vocab in
    )
    if all:
        cap = max(cap, len(all_due))
    elif len(all_due) > cap:
        await EventWriter(db, ksession.event_context(s, activity=ActivityType.RETRIEVAL)).emit(
            Verb.ADAPTED,
            ObjectType.SESSION,
            s.id,
            actor=Actor.SYSTEM,
            context={
                "what": f"review_cap={cap}",
                "why": f"mode={s.mode} energy={s.energy}",
                "reversible": True,
                "policy_version": "v1",
            },
        )
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
        confidence_pre=body.confidence_pre,
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
