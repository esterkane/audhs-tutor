"""Explicit feedback records and reversible preferences. Ratings are not mastery evidence."""

import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow_iso
from app.db.events import EventContext, EventWriter, Verb
from app.db.models import Assessment, QuestionFeedback
from app.kernel import curriculum, preferences
from app.schemas.areas import FeedbackIn
from app.schemas.common import Mode, ObjectType

GUIDANCE = {
    "questions.applied": "Prefer concrete application or debugging questions over recall of course wording.",
    "questions.connections": (
        "Where evidence supports it, ask learners to connect concepts "
        "and compare approaches from different sources."
    ),
    "questions.step_by_step": "Use one focused question at a time and offer a small hint before expanding the task.",
}


def out(row: QuestionFeedback) -> dict[str, Any]:
    return {
        "id": row.id,
        "target_key": row.target_key,
        "verdict": row.verdict,
        "labels": row.labels_json,
        "note": row.note,
        "created_at": row.created_at,
        "withdrawn": row.withdrawn_at is not None,
    }


async def record(db: AsyncSession, learner_id: str, body: FeedbackIn) -> QuestionFeedback:
    version = None
    if body.draft_id:
        draft = await curriculum.get_draft(db, learner_id, body.draft_id)
        if draft.version != body.draft_version:
            raise ValueError("draft changed; reload before rating this question")
        items = draft.payload_json.get("assessments", [])
        assert body.question_index is not None
        if body.question_index >= len(items):
            raise ValueError("question no longer exists")
        snapshot = items[body.question_index]
        version = draft.version
        prefix = f"draft:{draft.id}:"
    else:
        item = await db.get(Assessment, body.assessment_id)
        if item is None:
            raise KeyError("assessment not found")
        snapshot = {"kind": item.kind, "item": item.item_json, "skill_id": item.skill_id}
        prefix = f"assessment:{item.id}:"
    digest = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()[:24]
    row = QuestionFeedback(
        learner_id=learner_id,
        target_key=prefix + digest,
        draft_id=body.draft_id,
        assessment_id=body.assessment_id,
        draft_version=version,
        verdict=body.verdict,
        labels_json=list(dict.fromkeys(body.labels)),
        note=body.note.strip(),
        snapshot_json=snapshot,
    )
    db.add(row)
    await db.flush()
    events = EventWriter(db, EventContext(learner_id, None, Mode.STEADY, 3))
    await events.emit(
        Verb.PREFERRED,
        ObjectType.ITEM,
        row.target_key,
        result={
            "chosen_id": row.target_key if row.verdict == "good" else None,
            "rejected_id": row.target_key if row.verdict == "bad" else None,
            "reason": {"labels": row.labels_json, "note": row.note},
        },
        context={"feedback_id": row.id},
    )
    return row


async def summary(db: AsyncSession, learner_id: str) -> dict[str, Any]:
    rows = list(
        (
            await db.execute(
                select(QuestionFeedback)
                .where(QuestionFeedback.learner_id == learner_id)
                .order_by(QuestionFeedback.created_at.desc(), QuestionFeedback.id.desc())
            )
        ).scalars()
    )
    latest: dict[str, QuestionFeedback] = {}
    for row in rows:
        if not row.withdrawn_at:
            latest.setdefault(row.target_key, row)
    counts: dict[str, int] = {}
    for row in latest.values():
        for label in row.labels_json:
            counts[str(label)] = counts.get(str(label), 0) + 1
    prefs = await preferences.get_all(db, learner_id)
    rules = [
        ("questions.applied", {"good:useful_application", "bad:too_vague"}),
        ("questions.connections", {"good:connects_ideas"}),
        ("questions.step_by_step", {"bad:too_hard"}),
    ]
    suggestions = []
    for key, triggers in rules:
        matching = [
            r
            for r in latest.values()
            if any(f"{r.verdict}:{label}" in triggers for label in r.labels_json)
        ]
        if matching and not prefs[key]:
            suggestions.append(
                {
                    "key": key,
                    "description": GUIDANCE[key],
                    "reason": f"Suggested from your ratings on {len(matching)} distinct question(s): "
                    + ", ".join(
                        sorted(
                            {
                                str(label).replace("_", " ")
                                for r in matching
                                for label in r.labels_json
                            }
                        )
                    )
                    + ". This is a preference suggestion, not measured learning effectiveness.",
                }
            )
    return {
        "suggestions": suggestions,
        "feedback": [out(r) for r in rows[:100]],
        "label_counts": counts,
        "preferences": {k: bool(prefs[k]) for k in GUIDANCE},
    }


async def withdraw(db: AsyncSession, learner_id: str, feedback_id: str) -> None:
    row = await db.get(QuestionFeedback, feedback_id)
    if row is None or row.learner_id != learner_id:
        raise KeyError("feedback not found")
    if row.withdrawn_at:
        return
    row.withdrawn_at = utcnow_iso()
    events = EventWriter(db, EventContext(learner_id, None, Mode.STEADY, 3))
    await events.emit(
        Verb.UNDONE,
        ObjectType.ITEM,
        row.target_key,
        context={"what": "question feedback", "why": "learner withdrew rating", "reversible": True},
    )


async def set_guidance(db: AsyncSession, learner_id: str, key: str, enabled: bool) -> None:
    if key not in GUIDANCE:
        raise ValueError("unsupported question preference")
    events = EventWriter(db, EventContext(learner_id, None, Mode.STEADY, 3))
    await preferences.set_pref(
        db,
        learner_id,
        key,
        enabled,
        origin="proposed_accepted",
        events=events,
        policy_version="question-feedback-v1",
    )


async def guidance(db: AsyncSession, learner_id: str) -> list[str]:
    prefs = await preferences.get_all(db, learner_id)
    return [text for key, text in GUIDANCE.items() if prefs[key]]
