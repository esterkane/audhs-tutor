"""Append-only self-reports and observational delayed recall; no medical/causal inference."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.events import EventWriter, Verb
from app.db.models import LearningEvent
from app.kernel import blocks
from app.kernel import session as sessions
from app.schemas.common import ObjectType
from app.schemas.study_conditions import (
    ConditionRecall,
    ConditionsIn,
    ConditionsOut,
    ConditionsSummary,
    StudyConditions,
)


async def record(db: AsyncSession, learner_id: str, body: ConditionsIn) -> ConditionsOut:
    async with sessions.open_transition(db, body.session_id, learner_id) as session:
        if session.ended_at:
            raise AppError("session_ended", "Record conditions during an open session.", 409)
        state = await blocks.state(db, session)
        node_id = state.skill_id
        if not node_id:
            raise AppError(
                "no_learning_target", "Open a lesson before recording its conditions.", 409
            )
        event = await EventWriter(db, sessions.event_context(session)).emit(
            Verb.STUDY_CONDITIONS,
            ObjectType.SESSION,
            session.id,
            result={"conditions": body.conditions.model_dump()},
            context={"node_id": node_id, "self_reported": True},
            commit=False,
        )
        return ConditionsOut(id=event.id, node_id=node_id, conditions=body.conditions)


async def summary(db: AsyncSession, learner_id: str) -> ConditionsSummary:
    # A bounded, explicit window. Missing/changed conditions remain unknown, never inferred.
    cutoff = (datetime.now(UTC) - timedelta(days=90)).isoformat()
    events = list(
        (
            await db.scalars(
                select(LearningEvent)
                .where(
                    LearningEvent.learner_id == learner_id,
                    LearningEvent.ts >= cutoff,
                    LearningEvent.verb.in_(
                        [
                            str(Verb.STUDY_CONDITIONS),
                            str(Verb.ATTEMPTED),
                            str(Verb.EXPLAINED),
                            str(Verb.REVIEWED),
                        ]
                    ),
                )
                .order_by(LearningEvent.ts.desc(), LearningEvent.id.desc())
                .limit(10000)
            )
        ).all()
    )
    events.reverse()
    current: dict[tuple[str, str], LearningEvent] = {}
    exposures: dict[str, tuple[LearningEvent, StudyConditions | None]] = {}
    counted: set[str] = set()
    groups: dict[str, ConditionRecall] = {}
    for event in events:
        node = str((event.context_json or {}).get("node_id") or "")
        if not node:
            continue
        key = (event.session_id or "", node)
        if event.verb == str(Verb.STUDY_CONDITIONS):
            current[key] = event
        elif event.verb in (str(Verb.ATTEMPTED), str(Verb.EXPLAINED)):
            conditions = (
                StudyConditions.model_validate((current[key].result_json or {})["conditions"])
                if key in current
                else None
            )
            exposures[node] = (event, conditions)
        elif event.verb == str(Verb.REVIEWED):
            result = event.result_json or {}
            rating = result.get("rating")
            if (
                type(rating) is not int
                or rating not in (1, 2, 3, 4)
                or float(result.get("days_since_learned") or 0) < 1
            ):
                continue
            # One delayed outcome per item, from a different session at least a day later.
            if event.object_id in counted:
                continue
            review_at = datetime.fromisoformat(event.ts)
            exposure = exposures.get(node)
            if exposure is None:
                continue
            study, conditions = exposure
            if (
                conditions is None
                or study.session_id == event.session_id
                or review_at - datetime.fromisoformat(study.ts) < timedelta(days=1)
            ):
                continue
            group = conditions.model_dump_json()
            row = groups.setdefault(
                group, ConditionRecall(conditions=conditions, items_reviewed=0, recalled=0)
            )
            row.items_reviewed += 1
            row.recalled += int(rating >= 3)
            counted.add(event.object_id)
    return ConditionsSummary(groups=list(groups.values()))
