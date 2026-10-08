"""P8 code exercise routes. Running code is a browser matter (Pyodide worker); the backend hands
out the exercise, hints (one step at a time), the explicit full solution, and grades submissions
through `/api/assess/attempt` (kind `code`)."""

from typing import Any

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import DB, Learner
from app.core.errors import AppError
from app.db.events import EventWriter, Verb
from app.db.models import Assessment, AssessmentAttempt
from app.kernel import exercises, question_replacements, question_state, skill_graph
from app.kernel import session as ksession
from app.orchestrator import assessment_content
from app.schemas.common import ActivityType, ObjectType
from app.schemas.exercises import (
    CheckOut,
    ExerciseView,
    HintIn,
    HintOut,
    SolutionIn,
    SolutionOut,
    SourceOut,
)

router = APIRouter(prefix="/exercises", tags=["exercises"])


async def _check_content(db: DB, learner_id: str, a: Assessment) -> dict[str, Any] | None:
    check_id = a.item_json.get("check_assessment_id")
    if not check_id:
        return None
    try:
        check = await question_replacements.resolve(db, learner_id, str(check_id))
        return await assessment_content.snapshot(db, check.id, learner_id)
    except AppError as error:
        if error.code not in {
            "not_found",
            "assessment_unavailable",
            "question_replacement_invalid",
        }:
            raise
        # An unavailable linked question must not remove the runnable code workspace.
        return None


async def _view(db: DB, learner_id: str, a: Assessment) -> ExerciseView:
    a = await question_replacements.resolve(db, learner_id, a.id)
    content = await assessment_content.snapshot(db, a.id, learner_id)
    assessment_content.require_eligible(content)
    a = assessment_content.assessment(content)
    check_content = await _check_content(db, learner_id, a)
    check_available = check_content is not None
    item = exercises.public_item(a.item_json)
    node = await skill_graph.get_node(db, a.skill_id)
    node_slug = node.slug
    attempts = int(
        (
            await db.execute(
                select(func.count(AssessmentAttempt.id)).where(
                    AssessmentAttempt.assessment_id == a.id,
                    AssessmentAttempt.learner_id == learner_id,
                )
            )
        ).scalar_one()
    )
    return ExerciseView(
        assessment_id=a.id,
        content_version=assessment_content.token(content),
        check_content_version=assessment_content.token(check_content)
        if check_available and check_content is not None
        else None,
        skill_id=a.skill_id,
        exercise_id=str(item["exercise_id"]),
        title=str(item["title"]),
        prompt=str(item["prompt"]),
        starter_code=str(item["starter_code"]),
        success_criteria=list(item.get("success_criteria") or []),
        checks=[CheckOut(**c) for c in item.get("checks") or []],
        packages=list(item.get("packages") or []),
        timeout_s=int(item.get("timeout_s") or 10),
        max_output_chars=int(item.get("max_output_chars") or 20_000),
        sources=[SourceOut(**s) for s in item.get("sources") or []],
        runtime=str(item.get("runtime") or "pyodide-worker"),
        hints_available=len(a.item_json.get("hints") or []),
        attempts=attempts,
        check_assessment_id=str(check_content["id"]) if check_content else None,
        check_question="This check question is unavailable for practice."
        if a.item_json.get("check_assessment_id") and not check_available
        else str(check_content["item_json"].get("prompt") or "")
        if check_content
        else str(a.item_json.get("check_question") or ""),
        policy=exercises.policy_for(ex) if (ex := exercises.for_slug(node_slug)) else {},
    )


@router.get(
    "/for-skill/{skill_id}",
    summary="The code exercise for a skill (created once from the catalogue; 404 when none)",
    response_model=ExerciseView,
)
async def for_skill(skill_id: str, db: DB, learner: Learner) -> ExerciseView:
    node = await skill_graph.get_node(db, skill_id)
    a = await exercises.ensure_exercise(db, node)
    if a is None:
        raise AppError("not_found", "no code exercise for this skill yet", http_status=404)
    return await _view(db, learner.id, a)


async def _exercise(db: DB, assessment_id: str, learner_id: str) -> Assessment:
    a = await db.get(Assessment, assessment_id)
    if a is None or a.kind != exercises.KIND:
        raise AppError("not_found", "no such exercise", http_status=404)
    await question_state.require_active(db, learner_id, a.id)
    return a


@router.post(
    "/{assessment_id}/hint",
    summary="One hint step (hint-first; each level is an explicit request, logged)",
    response_model=HintOut,
)
async def hint(assessment_id: str, body: HintIn, db: DB, learner: Learner) -> HintOut:
    a = await _exercise(db, assessment_id, learner.id)
    session = await ksession.get(db, body.session_id)
    if session.learner_id != learner.id:
        raise AppError("not_found", "no such session", http_status=404)
    text, level = exercises.hint(a.item_json, body.level)
    events = EventWriter(db, ksession.event_context(session, activity=ActivityType.NEW_MATERIAL))
    await events.emit(
        Verb.EXPLAINED,
        ObjectType.ITEM,
        a.id,
        result={"sentences": max(1, text.count(". ") + 1), "cited_sources": []},
        context={"representation": "code_hint", "hint_count": level, "node_id": a.skill_id},
        representation="code_hint",
    )
    return HintOut(level=level, text=text, hints_available=len(a.item_json.get("hints") or []))


@router.post(
    "/{assessment_id}/solution",
    summary="The full solution — explicit request only, logged, followed by a check question",
    response_model=SolutionOut,
)
async def solution(assessment_id: str, body: SolutionIn, db: DB, learner: Learner) -> SolutionOut:
    a = await _exercise(db, assessment_id, learner.id)
    session = await ksession.get(db, body.session_id)
    if session.learner_id != learner.id:
        raise AppError("not_found", "no such session", http_status=404)
    events = EventWriter(db, ksession.event_context(session, activity=ActivityType.NEW_MATERIAL))
    await events.emit(
        Verb.EXPLAINED,
        ObjectType.ITEM,
        a.id,
        result={"sentences": 0, "cited_sources": []},
        context={
            "representation": "full_solution",
            "hint_count": len(a.item_json.get("hints") or []),
            "node_id": a.skill_id,
        },
        representation="full_solution",
    )
    check_text = str(a.item_json.get("check_question") or "")
    if a.item_json.get("check_assessment_id"):
        check = await _check_content(db, learner.id, a)
        check_text = (
            str(check["item_json"].get("prompt") or "")
            if check
            else "This check question is unavailable for practice."
        )
    return SolutionOut(
        solution=str(a.item_json.get("solution") or ""),
        check_question=check_text,
    )
