"""The one tutor loop (ADR-0007): interpret → identify skill → ContextPacket → retrieve → choose
action → stream generation → traces + events → checkpoint. Yields SSE-ready events."""

import time
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import new_id
from app.db.events import EventWriter, Verb
from app.db.traces import TutorTraceRecord, write_retrieval_trace, write_tutor_trace
from app.kernel import session as ksession
from app.kernel import skill_graph
from app.knowledge.repository import RetrievalRepository
from app.models_ai.gateway import ModelGateway, StreamHandle
from app.models_ai.provider import TaskClass
from app.orchestrator import actions, prompts, tools
from app.orchestrator.context import build_packet, render_messages
from app.schemas.common import ActivityType, ObjectType
from app.schemas.tutor import SourceRef, TurnDone, TurnMeta, TurnRequest

TASK_FOR_ACTION = {
    actions.Action.EXPLAIN: TaskClass.EXPLAIN_SIMPLE,
    actions.Action.HINT: TaskClass.HINT,
    actions.Action.FULL_SOLUTION: TaskClass.EXPLAIN_SIMPLE,
    actions.Action.SUMMARIZE: TaskClass.SUMMARIZE,
}


class TutorTurn:
    def __init__(self, db: AsyncSession, gateway: ModelGateway, repo: RetrievalRepository) -> None:
        self.db = db
        self.gateway = gateway
        self.repo = repo

    async def run(self, req: TurnRequest) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        t0 = time.perf_counter()
        db = self.db
        session = await ksession.get(db, req.session_id)
        if session.ended_at:
            raise ValueError("session already ended")
        learner_id = session.learner_id
        checkpoint = await ksession.load_checkpoint(db, session.id) or {}

        if req.skill_id:
            node = await skill_graph.get_node(db, req.skill_id)
        elif checkpoint.get("skill_id"):
            node = await skill_graph.get_node(db, checkpoint["skill_id"])
        else:
            nxt = await skill_graph.next_skill(db, learner_id)
            if nxt is None:
                raise ValueError("no skills seeded")
            node = nxt
        prev_hint = (
            int(checkpoint.get("hint_level", 0)) if checkpoint.get("skill_id") == node.id else 0
        )
        action, hint_level = actions.choose_action(req.text, req.action, prev_hint)
        block_type = "new_material"
        turn_id = new_id()

        events = EventWriter(
            db, ksession.event_context(session, activity=ActivityType.NEW_MATERIAL)
        )
        await events.emit(
            Verb.ASKED,
            ObjectType.TURN,
            turn_id,
            context={"text_len": len(req.text), "node_id": node.id},
        )

        yield (
            "meta",
            TurnMeta(
                turn_id=turn_id,
                session_id=session.id,
                skill_id=node.id,
                skill_title=node.title,
                action=str(action),
                hint_level=hint_level,
                prompt_version=prompts.PROMPT_VERSION,
                questioning_style="socratic" if session.socratic else "explicit",
            ).model_dump(),
        )

        result = await tools.retrieve(self.repo, f"{node.title}: {req.text}", skill_id=node.id, k=6)
        rtrace = await write_retrieval_trace(
            db, result.trace.model_copy(update={"learner_id": learner_id, "session_id": session.id})
        )
        packet = build_packet(
            policy=prompts.base_policy(),
            request=req.text,
            prompt_version=prompts.PROMPT_VERSION,
            preferences=await tools.get_preferences(db, learner_id),
            session_state=tools.session_state(
                session, node, block_type=block_type, hint_level=hint_level
            ),
            learning_contract=await tools.get_learning_contract(db, node),
            evidence=await tools.get_evidence(db, learner_id, node),
            retrieved=result.hits,
            output_contract=actions.output_contract(
                action,
                hint_level=hint_level,
                socratic=session.socratic,
                representation=req.representation,
                block_type=block_type,
            ),
        )
        messages = render_messages(packet)

        handle = StreamHandle()
        text = ""
        async for tok in self.gateway.stream(
            TASK_FOR_ACTION[action],
            messages,
            handle=handle,
            learner_id=learner_id,
            session_id=session.id,
            metadata={
                "prompt_version": prompts.PROMPT_VERSION,
                "skill_id": node.id,
                "turn_id": turn_id,
            },
        ):
            text += tok
            yield ("token", {"text": tok})

        sources = [
            SourceRef(
                chunk_id=c.chunk_id,
                citation=c.citation,
                trust_tier=c.trust_tier,
                score=c.score,
                flagged=c.flagged,
            )
            for c in packet.retrieved[:3]
        ]
        representation = actions.detect_representation(text)
        sentences = actions.count_sentences(text)
        latency_ms = int((time.perf_counter() - t0) * 1000)
        trace = await write_tutor_trace(
            db,
            TutorTraceRecord(
                learner_id=learner_id,
                session_id=session.id,
                turn_id=turn_id,
                action=str(action),
                prompt_version=prompts.PROMPT_VERSION,
                sections=packet.section_tokens,
                dropped=packet.dropped,
                model_call_id=handle.model_call_id,
                retrieval_trace_id=rtrace.id,
                latency_ms=latency_ms,
            ),
        )
        await events.emit(
            Verb.EXPLAINED,
            ObjectType.TURN,
            turn_id,
            result={"sentences": sentences, "cited_sources": [s.chunk_id for s in sources]},
            context={
                "representation": representation,
                "hint_count": hint_level,
                "model": handle.registry_id,
                "route": handle.route,
                "prompt_version": prompts.PROMPT_VERSION,
                "latency_ms": latency_ms,
                "tokens_in": handle.tokens_in,
                "tokens_out": handle.tokens_out,
                "cached_tokens": 0,
            },
            representation=representation,
        )
        await ksession.save_checkpoint(
            db,
            session,
            {
                "skill_id": node.id,
                "hint_level": hint_level,
                "turn_id": turn_id,
                "action": str(action),
                "section_tokens": packet.section_tokens,
                "dropped": packet.dropped,
            },
        )
        yield (
            "done",
            TurnDone(
                turn_id=turn_id,
                model_call_id=handle.model_call_id,
                tutor_trace_id=trace.id,
                registry_id=handle.registry_id,
                route=handle.route,
                sentences=sentences,
                representation=representation,
                sources=sources,
                flagged=sorted({f for c in packet.retrieved for f in c.flagged}),
                dropped=packet.dropped,
                latency_ms=latency_ms,
                text=text,
            ).model_dump(),
        )
