"""Explicit local help over one learner-owned, versioned research question."""

import hashlib
import hmac
import json
import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models import CurriculumDraft
from app.kernel import curriculum
from app.kernel.repetition_results import repetition_results
from app.knowledge.personal_memory import selected
from app.models_ai import registry
from app.models_ai.budget import Budget
from app.models_ai.gateway import ModelGateway
from app.models_ai.provider import Message, TaskClass
from app.orchestrator.context import escape_data
from app.orchestrator.prompts import PROMPTS_DIR
from app.schemas.knowledge_authoring import (
    KnowledgeResearch,
    NeutralObservationDiscussion,
    NeutralObservationSection,
    ResearchDiscussion,
    ResearchRepetitionRule,
    ResearchSectionDraft,
    ResearchTutorAnswer,
    ResearchTutorExchange,
    ResearchTutorIn,
    is_unmeasured_observation,
)

# Process-local integrity for an optimization, never a persistent question/source identity.
# Restarting invalidates reuse only; all saved replies and writing remain available.
_REUSE_KEY = secrets.token_bytes(32)


def reuse_token(binding: str, exchange: ResearchTutorExchange) -> str:
    serialized = json.dumps(
        exchange.model_dump(exclude={"cache_token"}), sort_keys=True, ensure_ascii=False
    )
    return hmac.new(_REUSE_KEY, (binding + serialized).encode(), hashlib.sha256).hexdigest()


async def help_research(
    db: AsyncSession,
    gateway: ModelGateway,
    learner_id: str,
    draft_id: str,
    command: ResearchTutorIn,
) -> tuple[CurriculumDraft, bool]:
    draft = await curriculum.get_draft(db, learner_id, draft_id)
    authoring = draft.payload_json.get("authoring") or {}
    if (
        draft.status != "draft"
        or draft.version != command.expected_version
        or not authoring.get("research")
    ):
        raise AppError(
            "research_changed",
            "Save and reload the editable research before asking the tutor.",
            409,
        )
    research = KnowledgeResearch.model_validate(authoring["research"])
    question = next((q for q in research.questions if q.id == command.question_id), None)
    if question is None:
        raise AppError(
            "research_question_missing", "This question is no longer in the saved research.", 409
        )
    if research.passage not in authoring["notes"]:
        raise AppError(
            "source_changed", "Review the changed source notes before asking the tutor.", 409
        )
    if not question.findings.strip():
        raise AppError(
            "research_findings_needed",
            "Write your findings first so the tutor can discuss your work.",
            422,
        )
    basis = {
        "passage": research.passage,
        "topic": research.topic,
        "question": question.prompt,
        "findings": question.findings,
        "evidence": question.evidence,
        "unresolved": question.unresolved,
        "section": question.section,
    }
    memories = await selected(db, learner_id, draft_id, question.memory_ids)
    # All source characters remain available; the model selects ids instead of copying quotations.
    passages = [research.passage[i : i + 1800] for i in range(0, len(research.passage), 1800)]
    verified = (
        repetition_results(research.passage, question.prompt)
        if "python" in research.passage.casefold()
        and not question.tutor_request.strip()
        and not question.unresolved.strip()
        else None
    )
    data = {
        **{k: v for k, v in basis.items() if k != "passage"},
        "source_passages": {str(i + 1): text for i, text in enumerate(passages)},
        "earlier_personal_notes": [m.model_dump() for m in memories],
        "request": question.tutor_request,
        "action": command.action,
        "recent_discussion": [
            {
                "request": x.request,
                "discussion": x.answer.discussion,
                "needs_check": x.answer.needs_check,
                "section": x.answer.section,
            }
            for x in ([] if command.refresh else question.tutor_exchanges[-2:])
        ],
    }
    if verified:
        with_results = {**data, "verified_repetition": verified.context()}
        if len(json.dumps(with_results, ensure_ascii=False)) <= 24000:
            data = with_results
        else:
            # An optimization must not displace saved evidence or reject a packet
            # that fits the established normal path.
            verified = None
    encoded = json.dumps(data, ensure_ascii=False)
    if len(question.tutor_exchanges) >= 12:
        raise AppError(
            "research_history_full",
            "This question has 12 saved tutor replies. Keep them and add a new research question to continue.",
            422,
        )
    if len(encoded) > 24000:
        raise AppError(
            "research_context_too_long",
            "Select a smaller passage or shorten the current findings/evidence to focus this request. "
            "Your saved text is kept.",
            422,
        )
    # Keep domain-specific demonstrations out of unrelated research packets.
    policy_name = (
        "curriculum/research-tutor.v11.md"
        if "python" in research.passage.casefold()
        else "curriculum/research-tutor.v10.md"
    )
    policy = (
        (PROMPTS_DIR / "_base/pedagogy.v2.md").read_text()
        + "\n\n"
        + (PROMPTS_DIR / policy_name).read_text()
        + "\n\n"
        + (PROMPTS_DIR / "curriculum/research-memory.v1.md").read_text()
        + "\n\n"
        + (
            PROMPTS_DIR
            / (
                "curriculum/research-repetition.v1.md"
                if verified
                else "curriculum/research-section.v2.md"
                if command.action == "draft"
                else "curriculum/research-discussion.v2.md"
            )
        ).read_text()
    )
    response_type = (
        ResearchRepetitionRule
        if verified
        else ResearchSectionDraft
        if command.action == "draft"
        else ResearchDiscussion
    )
    neutral_note = is_unmeasured_observation(research.passage)
    if neutral_note and not verified:
        response_type = (
            NeutralObservationSection if command.action == "draft" else NeutralObservationDiscussion
        )
    route = await gateway.router.resolve(db, TaskClass.EXPLAIN_SIMPLE, learner_id)
    spec = await registry.get_spec(db, route.registry_id)
    binding = json.dumps(
        {
            "learner": learner_id,
            "draft": draft_id,
            "question": question.id,
            "basis": basis,
            "memories": [m.model_dump() for m in memories],
            "request": question.tutor_request,
            "action": command.action,
            "policy": policy,
            "verified_results": verified.context() if verified else None,
            "coverage_contract": "literal-string-repetition.v1",
            "source_claim_contract": "neutral-observation.v2" if neutral_note else None,
            "schema": response_type.model_json_schema(),
            "route": route.model_dump(),
            "model": spec.model,
            "provider": spec.provider,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    latest = question.tutor_exchanges[-1] if question.tutor_exchanges else None
    if (
        not command.refresh
        and latest
        and latest.cache_token
        and hmac.compare_digest(latest.cache_token, reuse_token(binding, latest))
    ):
        return draft, True
    local = ModelGateway(
        db, gateway.router, {k: v for k, v in gateway.providers.items() if k == "ollama"}, Budget(0)
    )
    out = await local.complete(
        TaskClass.EXPLAIN_SIMPLE,
        [
            Message(
                role="system",
                content=policy,
            ),
            Message(
                role="user",
                content="<research_context>\n" + escape_data(encoded) + "\n</research_context>",
            ),
        ],
        response_model=response_type,
        learner_id=learner_id,
        max_tokens=1800,
        metadata={
            "task": "research_tutor",
            "structured_output": "native_schema",
            "draft_id": draft_id,
            "question_id": question.id,
            "action": command.action,
            "prompt_version": "curriculum." + policy_name.rsplit("/", 1)[-1].removesuffix(".md"),
            "memory_policy_version": "curriculum.research-memory.v1",
            "feedback_contract_version": "grounded-explanation.v5",
            "source_claim_contract": "neutral-observation.v2" if neutral_note else None,
            "coverage_contract": "literal-string-repetition.v1" if verified else None,
            "verified_result_count": len(verified.examples) if verified else 0,
            "verified_results_digest": hashlib.sha256(
                json.dumps(verified.context(), sort_keys=True, ensure_ascii=False).encode()
            ).hexdigest()
            if verified
            else None,
            "memory_ids": question.memory_ids,
        },
    )
    parsed = out.result.parsed
    if not isinstance(parsed, (ResearchDiscussion, ResearchSectionDraft, ResearchRepetitionRule)):
        raise AppError(
            "research_tutor_failed",
            "No complete source-linked reply returned. Your saved writing is unchanged.",
            422,
        )
    if any(index > len(passages) for index in parsed.source_indices):
        raise AppError(
            "research_source_mismatch",
            "The reply referred to an unavailable source passage. Your saved writing is unchanged.",
            422,
        )
    normalized = parsed.model_dump(exclude={"source_indices"})
    if isinstance(parsed, ResearchRepetitionRule) and verified:
        normalized = {
            "section" if command.action == "draft" else "discussion": verified.compose(parsed.rule)
        }
    elif isinstance(parsed, ResearchDiscussion):
        normalized["discussion"] = normalized.pop("answer_sentence")
    answer = ResearchTutorAnswer.model_validate(
        {
            **normalized,
            "source_quotes": [
                passages[index - 1] for index in dict.fromkeys(parsed.source_indices)
            ],
        }
    )
    if (
        not isinstance(answer, ResearchTutorAnswer)
        or any(
            not quote.strip() or len(quote) > 2000 or quote not in research.passage
            for quote in answer.source_quotes
        )
        or (command.action == "draft" and not answer.section.strip())
    ):
        raise AppError(
            "research_tutor_failed",
            "No complete source-linked reply returned. Your findings and section are saved unchanged.",
            422,
        )
    # Discussion never changes or offers a section unless explicitly requested.
    if command.action == "discuss":
        answer = answer.model_copy(update={"section": ""})
    exchange = ResearchTutorExchange(
        action=command.action,
        request=question.tutor_request,
        answer=answer,
        model_call_id=out.model_call_id,
        memories=memories,
    )
    if out.registry_id == route.registry_id and not out.hosted:
        exchange.cache_token = reuse_token(binding, exchange)
    question.tutor_exchanges.append(exchange)
    question.tutor_basis = json.dumps(basis, ensure_ascii=False, separators=(",", ":"))
    payload = {**draft.payload_json, "authoring": {**authoring, "research": research.model_dump()}}
    saved = await curriculum.update_draft(
        db, learner_id, draft_id, payload, expected_version=command.expected_version
    )

    return saved, False
