"""Local-only cross-course draft generation with bounded evidence and honest coverage."""

import asyncio
import json
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import PROJECT_ROOT, Settings
from app.db.models import CurriculumDraft, KnowledgeArea
from app.kernel import areas, curriculum, question_feedback
from app.kernel.assessment_quality import course_metadata, unsuitable_question
from app.models_ai.budget import Budget
from app.models_ai.factory import build_providers
from app.models_ai.gateway import ModelGateway
from app.models_ai.provider import Message, TaskClass
from app.models_ai.routing import Router
from app.orchestrator import prompts
from app.orchestrator.context import escape_data


class AreaLesson(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    goal: str = Field(min_length=10, max_length=500)
    exercise: str = Field(min_length=10, max_length=800)
    criteria: list[str] = Field(min_length=1, max_length=4)
    question: str = Field(min_length=10, max_length=800)
    expected_answer: str = Field(min_length=10, max_length=1200)
    source_ids: list[str] = Field(min_length=1, max_length=4)
    evidence_quote: str = Field(min_length=15, max_length=300)


class AreaSuggestion(BaseModel):
    lessons: list[AreaLesson] = Field(default_factory=list, max_length=3)


def local_gateway(db: AsyncSession, settings: Settings) -> ModelGateway:
    # Do not even construct hosted providers for this generation path.
    local = settings.model_copy(
        update={"openai_api_key": "", "anthropic_api_key": "", "daily_budget_usd": 0}
    )
    return ModelGateway(db, Router(local.routing_profile), build_providers(local), Budget(0))


def merge(
    area: KnowledgeArea,
    selected: list[dict[str, Any]],
    suggestion: AreaSuggestion,
    coverage: dict[str, Any],
) -> dict[str, Any]:
    by_id = {c["id"]: c for c in selected}
    skills, objects, assessments, rejected = [], [], [], []
    for i, lesson in enumerate(suggestion.lessons):
        citations = list(dict.fromkeys(lesson.source_ids))
        quote = " ".join(lesson.evidence_quote.split()).casefold()
        fields = [lesson.title, lesson.goal, lesson.question, lesson.exercise, *lesson.criteria]
        if (
            any(c not in by_id for c in citations)
            or any(course_metadata(t) for t in fields)
            or unsuitable_question(lesson.question)
            or not any(quote in " ".join(by_id[c]["text"].split()).casefold() for c in citations)
        ):
            rejected.append(lesson.title)
            continue
        slug = f"area-{area.slug}-{i + 1}-{curriculum.slugify(lesson.title)[:65]}"
        skills.append(
            {
                "slug": slug,
                "title": lesson.title,
                "description": lesson.goal,
                "prerequisites": [],
                "success_criteria": lesson.criteria,
                "assessment_requirements": {"dimensions": ["explanation"], "min_items": 1},
                "example_applications": [lesson.exercise],
            }
        )
        objects.append(
            {
                "skill": slug,
                "concept": lesson.title,
                "goal": lesson.goal,
                "examples": [],
                "exercises": [lesson.exercise],
                "success_criteria": lesson.criteria,
                "sources": citations,
            }
        )
        assessments.append(
            {
                "skill": slug,
                "kind": "explain_back",
                "source_chunk_id": citations[0],
                "origin": "area_model",
                "auto": False,
                "guessable": False,
                "item": {
                    "prompt": lesson.question,
                    "expected_answer": lesson.expected_answer,
                    "source_chunk_ids": citations,
                    "evidence_quote": lesson.evidence_quote,
                },
                "rubric": [
                    {
                        "criterion": "Answers the question with source-supported reasoning",
                        "description": lesson.expected_answer,
                        "weight": 1.0,
                        "required_terms": [],
                    }
                ],
            }
        )
    return {
        "domain": "programming" if area.slug == "python" else "ai_ml",
        "course": None,
        "section": None,
        "area_title": area.title,
        "skills": skills,
        "learning_objects": objects,
        "assessments": assessments,
        "area_coverage": coverage,
        "area_sources": [{k: v for k, v in c.items() if k != "text"} for c in selected],
        "area_rejected_lessons": rejected,
        "area_state": "generated" if skills else "needs_evidence",
    }


async def store_if_unchanged(
    db: AsyncSession,
    draft_id: str,
    version: int,
    payload: dict[str, Any],
    *,
    generated: bool = False,
    model_call_id: str | None = None,
) -> bool:
    values: dict[str, Any] = {"payload_json": payload}
    if generated:
        values.update(
            validation_json=curriculum.problems_json(
                await curriculum.validate_payload(db, payload)
            ),
            version=version + 1,
            origin="area_model",
            model_call_id=model_call_id,
        )
    result = await db.execute(
        update(CurriculumDraft)
        .where(
            CurriculumDraft.id == draft_id,
            CurriculumDraft.version == version,
            CurriculumDraft.status == "draft",
        )
        .values(**values)
        .returning(CurriculumDraft.id)
        .execution_options(synchronize_session=False)
    )
    changed = result.scalar_one_or_none() is not None
    await db.commit()
    return changed


async def create_or_generate(
    db: AsyncSession,
    settings: Settings,
    learner_id: str,
    area_id: str,
    gateway: ModelGateway | None = None,
    *,
    force_new: bool = False,
) -> tuple[str, str]:
    area = await areas.get(db, area_id)
    existing = (
        (
            await db.execute(
                select(CurriculumDraft)
                .where(
                    CurriculumDraft.learner_id == learner_id,
                    CurriculumDraft.area_id == area.id,
                    CurriculumDraft.status != "rejected",
                )
                .order_by(CurriculumDraft.updated_at.desc())
            )
        )
        .scalars()
        .first()
    )
    if force_new:
        existing = None
    retryable = (
        existing is not None
        and existing.status == "draft"
        and existing.version == 1
        and existing.origin == "area_scaffold"
    )
    if existing is not None and not retryable:
        return (
            existing.id,
            "existing",
        )  # never overwrite edits, published history or earlier reviews
    expected_version = existing.version if existing else None
    selected, coverage = await areas.excerpts(db, area)
    payload = merge(area, selected, AreaSuggestion(), coverage)
    draft = existing or await curriculum.create_draft(
        db,
        learner_id,
        course=None,
        section=None,
        area_id=area.id,
        payload=payload,
        origin="area_scaffold",
    )
    if not selected:
        return draft.id, "needs_evidence"
    version = expected_version if expected_version is not None else draft.version
    if not await store_if_unchanged(db, draft.id, version, {**payload, "area_state": "generating"}):
        return draft.id, "kept_edits"
    try:
        gw = gateway or local_gateway(db, settings)
        guidance = await question_feedback.guidance(db, learner_id)
        out = await gw.complete(
            TaskClass.GEN_ITEMS,
            [
                Message(
                    role="system",
                    content=prompts.base_policy()
                    + "\n\n"
                    + (PROJECT_ROOT / "prompts/curriculum/area.v1.md").read_text(),
                ),
                Message(
                    role="user",
                    content="Area: "
                    + escape_data(area.title)
                    + "\nExplicit preferences: "
                    + json.dumps(guidance)
                    + "\n<source_data>\n"
                    + escape_data(json.dumps(selected, ensure_ascii=False))
                    + "\n</source_data>",
                ),
            ],
            response_model=AreaSuggestion,
            learner_id=learner_id,
            max_tokens=2400,
            metadata={
                "task": "area_draft",
                "area_id": area.id,
                "prompt_version": "curriculum.area.v1",
            },
        )
        if not isinstance(out.result.parsed, AreaSuggestion):
            raise ValueError("no typed draft returned")
        generated = merge(area, selected, out.result.parsed, coverage)
        if not await store_if_unchanged(
            db, draft.id, version, generated, generated=True, model_call_id=out.model_call_id
        ):
            return draft.id, "kept_edits"
        await db.refresh(draft)
        return draft.id, str(generated["area_state"])
    except asyncio.CancelledError:
        draft_id = draft.id
        await db.rollback()
        await store_if_unchanged(db, draft_id, version, {**payload, "area_state": "interrupted"})
        raise
    except Exception as error:
        draft_id = draft.id
        await db.rollback()
        changed = await store_if_unchanged(
            db,
            draft_id,
            version,
            {
                **payload,
                "area_state": "generation_failed",
                "area_error": type(error).__name__
                + "; local generation could not finish. Draft kept for review.",
            },
        )
        return draft_id, "generation_failed" if changed else "kept_edits"
