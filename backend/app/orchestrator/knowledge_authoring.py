"""Local model proposals over explicitly selected learner material."""

import json
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models import CurriculumDraft
from app.kernel import curriculum, knowledge_authoring
from app.models_ai.budget import Budget
from app.models_ai.gateway import ModelGateway
from app.models_ai.provider import Message, TaskClass
from app.orchestrator.context import escape_data
from app.orchestrator.prompts import PROMPTS_DIR
from app.schemas.knowledge_authoring import (
    KnowledgeLessonSuggestion,
    KnowledgeMaterialInput,
    KnowledgeResearch,
    ResearchQuestion,
    SourceResearchQuestions,
)


async def suggest_research_questions(
    db: AsyncSession, gateway: ModelGateway, learner_id: str, draft_id: str, expected_version: int
) -> CurriculumDraft:
    gateway = ModelGateway(
        db, gateway.router, {k: v for k, v in gateway.providers.items() if k == "ollama"}, Budget(0)
    )
    draft = await curriculum.get_draft(db, learner_id, draft_id)
    authoring = draft.payload_json.get("authoring") or {}
    if (
        draft.status != "draft"
        or draft.version != expected_version
        or not authoring.get("research")
    ):
        raise AppError(
            "research_changed", "Save and reload your research before preparing questions.", 409
        )
    research = KnowledgeResearch.model_validate(authoring["research"])
    if any(
        q.findings or q.evidence or q.unresolved or q.section or q.tutor_exchanges
        for q in research.questions
    ):
        raise AppError(
            "research_started", "Keep your existing research. Edit or add a question yourself.", 409
        )
    if research.passage not in authoring["notes"]:
        raise AppError(
            "source_changed", "Restore the selected passage before preparing questions.", 409
        )
    out = await gateway.complete(
        TaskClass.GEN_ITEMS,
        [
            Message(
                role="system",
                content=(PROMPTS_DIR / "curriculum/research-questions.v1.md").read_text(),
            ),
            Message(
                role="user",
                content="<research_source>\n"
                + escape_data(
                    json.dumps(
                        {"topic": research.topic, "passage": research.passage}, ensure_ascii=False
                    )
                )
                + "\n</research_source>",
            ),
        ],
        response_model=SourceResearchQuestions,
        learner_id=learner_id,
        max_tokens=1800,
        metadata={
            "task": "research_questions",
            "draft_id": draft_id,
            "prompt_version": "curriculum.research-questions.v1",
        },
    )
    proposal = out.result.parsed
    if (
        not isinstance(proposal, SourceResearchQuestions)
        or any(
            not q.source_quote.strip() or q.source_quote not in research.passage
            for q in proposal.questions
        )
        or len({q.question.casefold().strip() for q in proposal.questions}) != 3
    ):
        raise AppError(
            "research_failed",
            "Questions lacked distinct prompts or exact source quotations. Your saved research is unchanged.",
            422,
        )
    from uuid import uuid4

    research.questions = [
        ResearchQuestion(id=str(uuid4()), prompt=q.question, source_quote=q.source_quote)
        for q in proposal.questions
    ]
    research.current = 0
    payload = {
        **draft.payload_json,
        "authoring": {
            **authoring,
            "research": research.model_dump(),
            "research_model_call_id": out.model_call_id,
        },
    }
    return await curriculum.update_draft(
        db, learner_id, draft_id, payload, expected_version=expected_version
    )


async def suggest_material(
    db: AsyncSession, gateway: ModelGateway, learner_id: str, draft_id: str, expected_version: int
) -> CurriculumDraft:
    # Retain the selected route but never construct a hosted authoring call.
    gateway = ModelGateway(
        db, gateway.router, {k: v for k, v in gateway.providers.items() if k == "ollama"}, Budget(0)
    )
    draft = await curriculum.get_draft(db, learner_id, draft_id)
    authoring = draft.payload_json.get("authoring")
    if not authoring or draft.status != "draft" or draft.version != expected_version:
        raise AppError("authoring_changed", "Reload the draft before generating.", 409)
    if len(authoring["notes"]) > 16000:
        raise AppError(
            "select_excerpt",
            "Edit the source notes to select up to 16,000 characters for generation.",
            422,
        )
    version = draft.version
    out = await gateway.complete(
        TaskClass.GEN_ITEMS,
        [
            Message(
                role="system",
                content=(PROMPTS_DIR / "curriculum/knowledge-authoring.v1.md").read_text(),
            ),
            Message(
                role="user",
                content="<learner_material>\n"
                + escape_data(
                    json.dumps(
                        {"title": authoring["title"], "notes": authoring["notes"]},
                        ensure_ascii=False,
                    )
                )
                + "\n</learner_material>",
            ),
        ],
        response_model=KnowledgeLessonSuggestion,
        learner_id=learner_id,
        max_tokens=2400,
        metadata={
            "task": "knowledge_authoring",
            "draft_id": draft_id,
            "prompt_version": "curriculum.knowledge-authoring.v1",
        },
    )
    if not isinstance(out.result.parsed, KnowledgeLessonSuggestion):
        raise AppError(
            "authoring_failed", "No complete proposal returned. Your notes are saved.", 422
        )
    command = KnowledgeMaterialInput.model_validate(
        {
            **{k: v for k, v in authoring.items() if k in KnowledgeMaterialInput.model_fields},
            **out.result.parsed.model_dump(),
        }
    )
    payload = await knowledge_authoring.payload_for(
        db,
        learner_id,
        command,
        authoring.get("skill_slug", "knowledge-" + UUID(authoring["request_id"]).hex),
        authoring,
    )
    payload["authoring"]["proposal_model_call_id"] = out.model_call_id
    # Version check prevents an inference finishing over newer learner edits.
    return await curriculum.update_draft(
        db, learner_id, draft_id, payload, expected_version=version
    )
