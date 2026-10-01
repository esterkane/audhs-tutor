"""Lazy rendering of a LearningObject into a Representation (ADR-0007). Cache first; otherwise one
gateway call with the standard ContextPacket, stored with its model_call id."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.events import EventWriter, Verb
from app.db.models import LearningObject, Representation, Session, SkillNode
from app.kernel import representations as krep
from app.kernel import session as ksession
from app.knowledge.repository import RetrievalRepository
from app.models_ai.gateway import ModelGateway
from app.models_ai.provider import TaskClass
from app.orchestrator import prompts, tools
from app.orchestrator.actions import count_sentences, trim_incomplete_tail
from app.orchestrator.context import build_packet, render_messages
from app.schemas.common import ActivityType, Actor, ObjectType


async def render(
    db: AsyncSession,
    gateway: ModelGateway,
    repo: RetrievalRepository,
    session: Session,
    node: SkillNode,
    kind: str,
    *,
    force: bool = False,
) -> dict[str, Any]:
    obj = await krep.object_for_skill(db, node.id)
    if obj is None:
        raise KeyError(f"no learning object for skill {node.slug}")
    evidence = await tools.get_evidence(db, session.learner_id, node)
    if kind not in krep.allowed_kinds(float(evidence.get("mastery", 0.0))):
        raise ValueError(f"representation {kind!r} not allowed yet for this node (mastery gate)")
    cached = None if force else await krep.get_cached(db, obj.id, kind)
    if cached is not None:
        return _out(
            obj, kind, cached.content, cached.id, cached.model_call_id, cached=True, sources=[]
        )

    result = await tools.retrieve(repo, f"{node.title}: {obj.concept}", skill_id=node.id, k=5)
    packet = build_packet(
        policy=prompts.base_policy(),
        request=f"Show the concept '{obj.concept}' as: {kind}. Goal: {obj.goal}",
        prompt_version=prompts.PROMPT_VERSION,
        preferences=await tools.get_preferences(db, session.learner_id),
        session_state=tools.session_state(session, node, block_type="new_material", hint_level=0),
        learning_contract=await tools.get_learning_contract(db, node),
        evidence=evidence,
        retrieved=result.hits,
        output_contract={
            "action": "representation",
            "representation": kind,
            "max_sentences": 12 if kind == "code" else 8,
            "citation_format": "source number in square brackets, e.g. [1]",
            "instructions": prompts.tutor_task("representation").strip(),
            "end_with": "one concrete next step",
        },
    )
    events = EventWriter(db, ksession.event_context(session, activity=ActivityType.NEW_MATERIAL))
    out = await gateway.complete(
        TaskClass.EXPLAIN_SIMPLE,
        render_messages(packet),
        learner_id=session.learner_id,
        session_id=session.id,
        metadata={
            "prompt_version": prompts.PROMPT_VERSION,
            "skill_id": node.id,
            "representation": kind,
        },
        max_tokens=420,
        events=events,
    )
    content = trim_incomplete_tail(out.result.text)
    row = await krep.store(db, obj.id, kind, content, model_call_id=out.model_call_id)
    await events.emit(
        Verb.EXPLAINED,
        ObjectType.EXPLANATION,
        row.id,
        actor=Actor.TUTOR,
        result={
            "sentences": count_sentences(content),
            "cited_sources": [h.chunk.id for h in result.hits[:3]],
        },
        context={
            "representation": kind,
            "hint_count": 0,
            "model": out.registry_id,
            "route": out.route,
            "prompt_version": prompts.PROMPT_VERSION,
            "latency_ms": out.result.latency_ms,
            "tokens_in": out.result.tokens_in,
            "tokens_out": out.result.tokens_out,
            "cached_tokens": out.result.cached_tokens,
        },
        representation=kind,
    )
    return _out(
        obj,
        kind,
        content,
        row.id,
        out.model_call_id,
        cached=False,
        sources=[h.chunk.provenance.citation() for h in result.hits[:3]],
    )


def _out(
    obj: LearningObject,
    kind: str,
    content: str,
    rep_id: str,
    model_call_id: str | None,
    *,
    cached: bool,
    sources: list[str],
) -> dict[str, Any]:
    return {
        "object_id": obj.id,
        "skill_id": obj.skill_id,
        "concept": obj.concept,
        "kind": kind,
        "content": content,
        "representation_id": rep_id,
        "model_call_id": model_call_id,
        "cached": cached,
        "sources": sources,
    }


async def prefer(
    db: AsyncSession, session: Session, chosen_id: str, rejected_id: str, reason: str | None = None
) -> None:
    """The learner chose one representation over another: a preference pair (ADR-0005 signal)."""
    chosen = await db.get(Representation, chosen_id)
    rejected = await db.get(Representation, rejected_id)
    if chosen is None or rejected is None:
        raise KeyError("representation not found")
    events = EventWriter(db, ksession.event_context(session))
    await events.emit(
        Verb.PREFERRED,
        ObjectType.EXPLANATION,
        chosen_id,
        result={"chosen_id": chosen_id, "rejected_id": rejected_id, "reason": reason},
        context={"representation_chosen": chosen.kind, "representation_rejected": rejected.kind},
    )
