"""Model-assisted curriculum drafting (P4). The routed local model (`TaskClass.GEN_ITEMS`) is asked
for learning objectives, exercises and one MCQ per lecture, *from quoted source excerpts only*. The
result is merged into the deterministic draft as a proposal with `origin="model"`: it is untrusted
until the learner reviews and publishes it (ADR-0008), and the call is logged like every model call.
Without a ready route the caller falls back to the deterministic draft."""

from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.kernel import curriculum
from app.models_ai.budget import BudgetExceeded
from app.models_ai.gateway import GatewayError, ModelGateway
from app.models_ai.provider import Message, ProviderError, TaskClass
from app.models_ai.routing import NoModelReady
from app.orchestrator import prompts
from app.orchestrator.context import escape_data

MAX_EXCERPT_CHARS = 1200
MAX_LECTURES = 12


class LessonSuggestion(BaseModel):
    slug: str
    goal: str = Field(max_length=400)
    success_criteria: list[str] = Field(default_factory=list, max_length=4)
    exercises: list[str] = Field(default_factory=list, max_length=3)
    mcq_question: str | None = Field(default=None, max_length=300)
    mcq_options: list[str] = Field(default_factory=list, max_length=4)
    mcq_answer: int | None = None
    mcq_explanation: str | None = Field(default=None, max_length=300)


class DraftSuggestions(BaseModel):
    lessons: list[LessonSuggestion] = Field(default_factory=list)


def _excerpts(mat: curriculum.SectionMaterial) -> str:
    """Quoted excerpts, one tagged block per lecture. The slug is the same one the deterministic
    draft uses; the title goes on its own line (never inside an attribute a quote could break)."""
    parts = ["<source_excerpts>"]
    for lec, slug in zip(mat.lectures[:MAX_LECTURES], curriculum.lecture_slugs(mat), strict=False):
        text = " ".join(curriculum._body(c["text"]) for c in lec["chunks"][:4])[:MAX_EXCERPT_CHARS]
        parts.append(f'<lecture slug="{slug}">')
        parts.append("title: " + escape_data(str(lec["lecture"])).replace("\n", " "))
        parts.append(escape_data(text))
        parts.append("</lecture>")
    parts.append("</source_excerpts>")
    return "\n".join(parts)


async def draft_with_model(
    db: AsyncSession,
    gateway: ModelGateway,
    learner_id: str,
    *,
    course: str,
    section: str | None,
) -> tuple[dict[str, Any], str | None]:
    """Deterministic payload + model suggestions merged in (goal, criteria, exercises, one MCQ per
    lecture). Returns (payload, model_call_id). If the model route is unavailable the payload is
    the deterministic one and the id is None."""
    mat = await curriculum.section_material(db, course, section)
    if not mat.lectures:
        raise ValueError(curriculum.no_primary_message(mat, course, section))
    payload = curriculum.propose_payload(mat)
    payload["selection"] = curriculum.selection_summary(mat)  # excluded text never reaches here
    try:
        out = await gateway.complete(
            TaskClass.GEN_ITEMS,
            [
                Message(role="system", content=prompts.curriculum_task("draft")),
                Message(
                    role="user",
                    content=_excerpts(mat) + "\nReturn one entry per lecture slug listed above.",
                ),
            ],
            response_model=DraftSuggestions,
            learner_id=learner_id,
            metadata={
                "task": "curriculum_draft",
                "course": course,
                "section": section,
                "prompt_version": prompts.CURRICULUM_VERSION,
            },
            max_tokens=1600,
        )
    except (NoModelReady, GatewayError, ProviderError, BudgetExceeded):
        return payload, None  # no ready route / model failure: the deterministic draft stands
    gen = out.result.parsed
    if not isinstance(gen, DraftSuggestions):
        return payload, out.model_call_id
    by_slug = {s["slug"]: s for s in payload["skills"]}
    objects = {o["skill"]: o for o in payload["learning_objects"]}
    for sug in gen.lessons:
        skill = by_slug.get(sug.slug)
        obj = objects.get(sug.slug)
        if skill is None or obj is None:
            continue  # the model may not invent lectures
        # every replaced field is labelled so the UI can say which lessons the model touched
        if sug.goal.strip():
            obj["goal"] = sug.goal.strip()
            obj["origin"] = "model"
        if sug.success_criteria:
            skill["success_criteria"] = [c.strip() for c in sug.success_criteria if c.strip()][:4]
            skill["origin"] = "model"
        if sug.exercises:
            obj["exercises"] = [e.strip() for e in sug.exercises if e.strip()][:3]
            obj["origin"] = "model"
        if (
            sug.mcq_question
            and len(sug.mcq_options) == 4
            and sug.mcq_answer is not None
            and 0 <= sug.mcq_answer < 4
        ):
            payload["assessments"].append(
                {
                    "skill": sug.slug,
                    "kind": "mcq",
                    "item": {
                        "question": sug.mcq_question.strip(),
                        "options": [o.strip() for o in sug.mcq_options],
                        "answer": sug.mcq_answer,
                        "explanation": (sug.mcq_explanation or "").strip(),
                    },
                    # the model saw up to 4 excerpts; no single passage is *the* source, so none
                    # is claimed (the validator warns; `auto` is reserved for source-cut items)
                    "source_chunk_id": None,
                    "auto": False,
                    "origin": "model",
                }
            )
    return payload, out.model_call_id
