"""P7: one model-proposed comprehension question per clip (`TaskClass.GEN_ITEMS`), grounded in the
clip's transcript only and checked deterministically before it is stored; a `listened`/`attempted`
never depends on the model. Without a ready route the kernel's deterministic cloze is used."""

from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.kernel import listening
from app.kernel.curriculum import STOP_WORDS
from app.models_ai.budget import BudgetExceeded
from app.models_ai.gateway import GatewayError, ModelGateway
from app.models_ai.provider import Message, ProviderError, TaskClass
from app.models_ai.routing import NoModelReady
from app.orchestrator import prompts
from app.orchestrator.context import escape_data

MAX_TRANSCRIPT_CHARS = 2500


class ComprehensionQuestion(BaseModel):
    question: str = Field(max_length=300)
    options: list[str] = Field(min_length=4, max_length=4)
    answer: int = Field(ge=0, le=3)
    explanation: str = Field(default="", max_length=400)


def validate_question(q: ComprehensionQuestion, transcript: str) -> list[str]:
    """Deterministic checks: shape, distinct non-empty options, the explanation quotes the clip."""
    problems: list[str] = []
    opts = [o.strip() for o in q.options]
    if any(not o for o in opts):
        problems.append("empty option")
    if len({o.lower() for o in opts}) != 4:
        problems.append("options are not distinct")
    if not q.question.strip().endswith("?") and len(q.question.split()) < 3:
        problems.append("question too short")
    low = transcript.lower()

    def content_words(text: str) -> list[str]:
        return [
            w.strip(".,;:!?\"'").lower()
            for w in text.split()
            if len(w.strip(".,;:!?\"'")) >= 5 and w.lower() not in STOP_WORDS
        ]

    correct = opts[q.answer] if 0 <= q.answer < 4 else ""
    words = content_words(correct)
    if words and not any(w in low for w in words):
        problems.append("correct option shares no word with the transcript")
    # a lone echo of the transcript would give the answer away when the text is visible
    echoing = sum(1 for o in opts if any(w in low for w in content_words(o)))
    if echoing < 2:
        problems.append(
            "distractors share nothing with the clip (the correct option would stand out)"
        )
    return problems


async def propose_question(
    db: AsyncSession,
    gateway: ModelGateway,
    *,
    learner_id: str,
    session_id: str | None,
    transcript: str,
    language: str | None,
    skill_id: str | None = None,
) -> tuple[dict[str, Any] | None, str | None, list[str]]:
    """(item, model_call_id, problems). item None when no route is ready or the reply fails the
    deterministic checks — the caller falls back to a source-cut cloze."""
    clip = escape_data(transcript[:MAX_TRANSCRIPT_CHARS])
    user = (
        f'<clip_transcript lang="{escape_data(language or "unknown")}">\n{clip}\n</clip_transcript>\n'
        "Return one question with four options."
    )
    try:
        out = await gateway.complete(
            TaskClass.GEN_ITEMS,
            [
                Message(role="system", content=prompts.listening_task("comprehension")),
                Message(role="user", content=user),
            ],
            response_model=ComprehensionQuestion,
            learner_id=learner_id,
            session_id=session_id,
            metadata={
                "task": "listening_question",
                "prompt_version": prompts.LISTENING_VERSION,
                "skill_id": skill_id,
            },
            max_tokens=400,
        )
    except (NoModelReady, GatewayError, ProviderError, BudgetExceeded):
        return None, None, ["model route unavailable"]
    q = out.result.parsed
    if not isinstance(q, ComprehensionQuestion):
        return None, out.model_call_id, ["no parsed question"]
    problems = validate_question(q, transcript)
    if problems:
        return None, out.model_call_id, problems
    return (
        {
            "kind": "mcq",
            "item": {
                "question": q.question.strip(),
                "options": [o.strip() for o in q.options],
                "answer": q.answer,
                "explanation": q.explanation.strip(),
            },
        },
        out.model_call_id,
        [],
    )


async def ensure_task(
    db: AsyncSession,
    gateway: ModelGateway,
    *,
    lesson: listening.Lesson,
    section: listening.Section,
    learner_id: str,
    session_id: str,
    use_model: bool,
) -> tuple[Any, list[str]]:
    """The one task for a clip: existing row, else a model proposal (checked) or the source-cut
    cloze. Returns (assessment, problems-with-the-model-proposal)."""
    node = await listening.listening_node(db, lesson.language or "unknown")
    a = await listening.existing_task(db, node.id, section.chunk_id)
    if a is not None:
        return a, []
    problems: list[str] = []
    proposal, call_id = None, None
    if use_model:
        proposal, call_id, problems = await propose_question(
            db,
            gateway,
            learner_id=learner_id,
            session_id=session_id,
            transcript=section.text,
            language=lesson.language,
            skill_id=node.id,
        )
    if proposal is not None:
        a = await listening.store_task(
            db,
            node,
            lesson,
            section,
            kind=proposal["kind"],
            item=proposal["item"],
            origin="model",
            model_call_id=call_id,
        )
    else:
        det = listening.deterministic_task(section)
        if det is None:  # load_lesson filters these out; defensive
            raise ValueError("this clip's transcript offers no usable task")
        a = await listening.store_task(
            db,
            node,
            lesson,
            section,
            kind=det["kind"],
            item=det["item"],
            origin="deterministic",
            model_call_id=None,
        )
    # two concurrent first requests: keep the oldest row, drop ours
    first = await listening.existing_task(db, node.id, section.chunk_id)
    if first is not None and first.id != a.id:
        await db.delete(a)
        await db.commit()
        return first, problems
    return a, problems
