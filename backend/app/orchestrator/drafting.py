"""Model-assisted curriculum drafting (P4). The routed local model (`TaskClass.GEN_ITEMS`) is asked
for learning objectives, exercises and one MCQ per lecture, *from quoted source excerpts only*. The
result is merged into the deterministic draft as a proposal with `origin="model"`: it is untrusted
until the learner reviews and publishes it (ADR-0008), and the call is logged like every model call.
Without a ready route the caller falls back to the deterministic draft."""

import re
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

MAX_EXCERPT_CHARS = 1600
MAX_LECTURES = 12
EXCERPTS_PER_LECTURE = 4
# One call per few lectures: a whole section in one reply overran the local models' output limit
# ("output is incomplete due to a max_tokens length limit" on gemma3:12b and llama3.1:8b for 8
# lectures, 2026-09-21). Bounded per call, merged deterministically.
LECTURES_PER_CALL = 3
MAX_TOKENS_PER_CALL = 2000


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


_FENCE = re.compile(r"```.*?```", re.S)
_SETUP_LINE = re.compile(r"^\s*(?:[!%]|pip\s+install|apt\s+install|import\s|from\s+\S+\s+import\s)")


def prose_words(text: str) -> int:
    """Words outside fenced code: the teaching text of a passage. Setup cells (installs, imports)
    and bare code have none, so they never displace an explanation in the excerpts."""
    body = _FENCE.sub(" ", curriculum._body(text))
    body = "\n".join(line for line in body.splitlines() if not _SETUP_LINE.match(line))
    return len(re.findall(r"[A-Za-zÀ-ÿ]{3,}", body))


def teaching_chunks(
    chunks: list[dict[str, Any]], n: int = EXCERPTS_PER_LECTURE
) -> list[dict[str, Any]]:
    """Up to `n` passages with the most teaching text, in source order. A notebook opens with
    `pip install` and imports; quoting only those made the local model propose lessons about
    installing packages (2026-09-21). If no passage has prose, the first `n` are used."""
    scored = sorted(enumerate(chunks), key=lambda ic: (-prose_words(str(ic[1]["text"])), ic[0]))
    picked = [ic for ic in scored[:n] if prose_words(str(ic[1]["text"])) > 0]
    if not picked:
        return chunks[:n]
    return [c for _, c in sorted(picked, key=lambda ic: ic[0])]


def _excerpts(mat: curriculum.SectionMaterial, start: int = 0, stop: int | None = None) -> str:
    """Quoted excerpts, one tagged block per lecture in `[start, stop)`. The slug is the same one the
    deterministic draft uses; the title goes on its own line (never inside an attribute a quote could
    break)."""
    parts = ["<source_excerpts>"]
    pairs = list(zip(mat.lectures[:MAX_LECTURES], curriculum.lecture_slugs(mat), strict=False))
    for lec, slug in pairs[start:stop]:
        text = " ".join(curriculum._body(c["text"]) for c in teaching_chunks(lec["chunks"]))[
            :MAX_EXCERPT_CHARS
        ]
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
) -> tuple[dict[str, Any], str | None, list[str]]:
    """Deterministic payload + model suggestions merged in (goal, criteria, exercises, one MCQ per
    lecture), asked for `LECTURES_PER_CALL` lectures at a time. Returns (payload, model_call_id of
    the first successful call, titles of lectures whose call failed and therefore stayed
    deterministic). If no call succeeds the payload is the deterministic one and the id is None."""
    mat = await curriculum.section_material(db, course, section)
    if not mat.lectures:
        raise ValueError(curriculum.no_primary_message(mat, course, section))
    payload = curriculum.propose_payload(mat)
    payload["selection"] = curriculum.selection_summary(mat)  # excluded text never reaches here
    lectures = mat.lectures[:MAX_LECTURES]
    call_id: str | None = None
    failed: list[str] = []
    lessons: list[LessonSuggestion] = []
    for start in range(0, len(lectures), LECTURES_PER_CALL):
        stop = start + LECTURES_PER_CALL
        try:
            out = await gateway.complete(
                TaskClass.GEN_ITEMS,
                [
                    Message(role="system", content=prompts.curriculum_task("draft")),
                    Message(
                        role="user",
                        content=_excerpts(mat, start, stop)
                        + "\nReturn one entry per lecture slug listed above.",
                    ),
                ],
                response_model=DraftSuggestions,
                learner_id=learner_id,
                metadata={
                    "task": "curriculum_draft",
                    "course": course,
                    "section": section,
                    "lectures": f"{start + 1}-{min(stop, len(lectures))}/{len(lectures)}",
                    "prompt_version": prompts.CURRICULUM_VERSION,
                },
                max_tokens=MAX_TOKENS_PER_CALL,
            )
        except (NoModelReady, GatewayError, ProviderError, BudgetExceeded):
            # no ready route / model failure for this group: those lessons stay deterministic
            failed.extend(str(lec["title"]) for lec in lectures[start:stop])
            continue
        call_id = call_id or out.model_call_id
        gen = out.result.parsed
        if isinstance(gen, DraftSuggestions):
            lessons.extend(gen.lessons)
        else:
            failed.extend(str(lec["title"]) for lec in lectures[start:stop])
    if call_id is None:
        return payload, None, failed
    by_slug = {s["slug"]: s for s in payload["skills"]}
    objects = {o["skill"]: o for o in payload["learning_objects"]}
    lecture_pairs = list(zip(lectures, curriculum.lecture_slugs(mat), strict=False))
    for sug in lessons:
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
            # the explain-back rubric follows the criteria the learner will be shown
            lec = next((lec for lec, s in lecture_pairs if s == sug.slug), None)
            for a in payload["assessments"]:
                if a["skill"] == sug.slug and a["kind"] == "explain_back":
                    a["rubric"] = curriculum.rubric_from_criteria(
                        skill["success_criteria"],
                        curriculum.salient_terms(
                            [str(c["text"]) for c in (lec or {}).get("chunks", [])]
                        ),
                    )
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
    return payload, call_id, failed
