"""Critical-thinking challenge modes (ADR-0003, opt-in blocks): planted error, steelman, teach-back,
calibration. The generator is an LLM call with a structured schema; the item becomes an Assessment
(kind = challenge_<mode>) graded by the hierarchical grader; every challenge schedules a delayed item."""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Assessment, AssessmentRubric, MemoryState, Session, SkillNode
from app.kernel import memory
from app.kernel import session as ksession
from app.knowledge.repository import RetrievalRepository
from app.models_ai.gateway import ModelGateway
from app.models_ai.provider import Message, TaskClass
from app.orchestrator import prompts, tools
from app.orchestrator.context import build_packet, data_block, render_messages
from app.schemas.challenge import CHALLENGE_MODES, ChallengeItem, ChallengeView

DELAY_DAYS = 2
DIMENSION_FOR_MODE = {
    "planted_error": "application",
    "steelman": "transfer",
    "teach_back": "explanation",
    "calibration": "recall",
}


def kind_for(mode: str) -> str:
    return f"challenge_{mode}"


async def existing(
    db: AsyncSession, learner_id: str, node: SkillNode, mode: str
) -> Assessment | None:
    """Reuse an unattempted generated challenge for this skill+mode (they are expensive to make)."""
    from app.db.models import AssessmentAttempt

    stmt = select(Assessment).where(
        Assessment.skill_id == node.id, Assessment.kind == kind_for(mode)
    )
    for a in (await db.execute(stmt)).scalars():
        tried = (
            await db.execute(
                select(AssessmentAttempt.id)
                .where(
                    AssessmentAttempt.assessment_id == a.id,
                    AssessmentAttempt.learner_id == learner_id,
                )
                .limit(1)
            )
        ).first()
        if not tried:
            return a
    return None


async def start(
    db: AsyncSession,
    gateway: ModelGateway,
    repo: RetrievalRepository,
    session: Session,
    node: SkillNode,
    mode: str,
) -> ChallengeView:
    if mode not in CHALLENGE_MODES:
        raise ValueError(f"unknown challenge mode {mode!r}")
    prior = await existing(db, session.learner_id, node, mode)
    if prior is not None:
        item = prior.item_json
        return ChallengeView(
            assessment_id=prior.id,
            skill_id=node.id,
            mode=mode,
            prompt=item["prompt"],
            criteria=item.get("criteria", []),
            cached=True,
            sources=item.get("sources", []),
        )

    result = await tools.retrieve(repo, f"{node.title}: {node.description}", skill_id=node.id, k=5)
    packet = build_packet(
        policy=prompts.base_policy(),
        request=f"Create a {mode.replace('_', ' ')} challenge for the skill '{node.title}'.",
        prompt_version=prompts.PROMPT_VERSION,
        session_state=tools.session_state(session, node, block_type="challenge", hint_level=0),
        learning_contract=await tools.get_learning_contract(db, node),
        evidence=await tools.get_evidence(db, session.learner_id, node),
        retrieved=result.hits,
        output_contract={
            "action": f"challenge_{mode}",
            "instructions": prompts.challenge_task(mode).strip(),
            "citation_format": "[n]",
        },
    )
    from app.db.events import EventWriter
    from app.schemas.common import ActivityType

    events = EventWriter(db, ksession.event_context(session, activity=ActivityType.CHALLENGE))
    out = await gateway.complete(
        TaskClass.GEN_ITEMS,
        render_messages(packet),
        response_model=ChallengeItem,
        learner_id=session.learner_id,
        session_id=session.id,
        metadata={"prompt_version": prompts.PROMPT_VERSION, "challenge": mode},
        max_tokens=700,
        events=events,
    )
    gen = out.result.parsed
    assert isinstance(gen, ChallengeItem)
    rubric = AssessmentRubric(
        criteria_json=[{"criterion": c, "keywords": _keywords(c)} for c in gen.criteria], version=1
    )
    db.add(rubric)
    await db.flush()
    sources = [h.chunk.provenance.citation() for h in result.hits[:3]]
    a = Assessment(
        skill_id=node.id,
        kind=kind_for(mode),
        rubric_id=rubric.id,
        item_json={
            "prompt": gen.prompt,
            "hidden_key": gen.hidden_key,
            "criteria": gen.criteria,
            "mode": mode,
            "sources": sources,
            "model_call_id": out.model_call_id,
            "grounding": data_block(packet.retrieved)[:2000],
        },
    )
    db.add(a)
    await db.commit()
    return ChallengeView(
        assessment_id=a.id,
        skill_id=node.id,
        mode=mode,
        prompt=gen.prompt,
        criteria=gen.criteria,
        cached=False,
        sources=sources,
    )


def _keywords(criterion: str) -> list[str]:
    """Rough rubric keywords from the criterion text (words ≥ 6 chars); the LLM grader does the real work."""
    import re

    words = [w.lower() for w in re.findall(r"[A-Za-z_]{6,}", criterion)]
    stop = {
        "answer",
        "learner",
        "correct",
        "correctly",
        "explains",
        "explain",
        "states",
        "identifies",
        "gives",
        "keeps",
        "covers",
        "should",
        "before",
        "after",
        "where",
        "which",
        "there",
        "their",
    }
    return [w for w in words if w not in stop][:4]


async def schedule_delayed(
    db: AsyncSession, learner_id: str, assessment: Assessment, *, now: datetime | None = None
) -> str:
    """Every challenge ends with a delayed review item (pedagogy guardrails): due in DELAY_DAYS."""
    now = now or datetime.now(UTC)
    item, ms = await memory.ensure_item(
        db,
        learner_id,
        assessment.skill_id,
        assessment.kind,
        {"ref": assessment.id, "assessment_id": assessment.id},
        now=now,
    )
    due = (now + timedelta(days=DELAY_DAYS)).isoformat(timespec="milliseconds")
    row = (
        await db.execute(select(MemoryState).where(MemoryState.review_item_id == item.id))
    ).scalar_one()
    if row.last_review is None:
        row.due = due
        await db.commit()
    return row.due


def grader_messages(item: dict[str, Any], answer_block: str) -> list[Message]:
    """Messages for the LLM grade of a challenge answer: the hidden key is the reference."""
    user = "\n\n".join(
        [
            prompts.grader_task("explain_back").strip(),
            f"## Challenge\n{item['prompt']}",
            f"## Reference (hidden from the learner)\n{item['hidden_key']}",
            "## Rubric criteria\n" + "\n".join(f"- {c}" for c in item.get("criteria", [])),
            "## Learner answer\n" + answer_block,
            "Return criterion_results in the same order as the rubric.",
        ]
    )
    return [
        Message(role="system", content=prompts.base_policy()),
        Message(role="user", content=user),
    ]
