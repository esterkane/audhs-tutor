"""The one tutor loop (ADR-0007): interpret → identify skill → ContextPacket → retrieve → choose
action → stream generation → traces + events → checkpoint. Yields SSE-ready events.

A turn without a trace is a bug: the tutor_trace is written in a `finally`, also when the client
aborts the stream mid-way (the explanation is then flagged partial)."""

import dataclasses
import re
import time
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import new_id
from app.db.events import EventWriter, Verb
from app.db.models import ExperimentArm
from app.db.traces import TutorTraceRecord, write_retrieval_trace, write_tutor_trace
from app.kernel import experiments, practice, representations, skill_graph
from app.kernel import session as ksession
from app.knowledge.repository import RetrievalRepository
from app.models_ai.gateway import GatewayError, ModelGateway, StreamHandle
from app.models_ai.provider import TaskClass
from app.orchestrator import actions, prompts, tools
from app.orchestrator.context import QUARANTINE_BELOW_TRUST, build_packet, render_messages
from app.schemas.common import ActivityType, Actor, Domain, ObjectType
from app.schemas.tutor import SourceRef, TurnDone, TurnMeta, TurnRequest

MAX_TOKENS_FOR_ACTION = {  # ~25 tokens per sentence; the cap backs up the prompt's sentence limit
    actions.Action.EXPLAIN: 190,
    actions.Action.HINT: 95,
    actions.Action.FULL_SOLUTION: 700,
    actions.Action.SUMMARIZE: 160,
}
SOCRATIC_MAX_TOKENS = 120
TASK_FOR_ACTION = {
    actions.Action.EXPLAIN: TaskClass.EXPLAIN_SIMPLE,
    actions.Action.HINT: TaskClass.HINT,
    actions.Action.FULL_SOLUTION: TaskClass.EXPLAIN_SIMPLE,
    actions.Action.SUMMARIZE: TaskClass.SUMMARIZE,
}
ACTIVITY_FOR_ACTION = {
    actions.Action.SUMMARIZE: ActivityType.RECAP,
}


_TRAILING = re.compile(r"(\s*\[[\d,\s]+\]|[\s\"')\]*])+$")


def socratic_delivered(text: str) -> bool:
    """A Socratic turn asks one narrowing question and stays short: its last sentence contains a
    question (trailing `[n]` citations and quotes ignored) and the turn has ≤ 6 sentences (the
    guardrails allow 2–3 concrete options after the question)."""
    body = _TRAILING.sub("", text.strip())
    if not body:
        return False
    segments = re.split(r"(?<=[.!?])\s+", body)
    # the question may be followed by the 2–3 concrete options the guardrails ask for
    asks = any("?" in seg for seg in segments[-2:]) or body.endswith("?")
    return asks and actions.count_sentences(body) <= 6


def arm_fidelity(
    arm_config: dict[str, Any] | None,
    *,
    text: str,
    completed: bool,
    arm_not_applied: bool,
    detected_representation: str | None = None,
) -> dict[str, Any]:
    """`arm_intended` / `arm_delivered` for the `explained` event. No arm → no keys. A cancelled
    stream gives no verdict (intent only). Only a *Socratic* arm can fail by 'explained instead of
    asked' — an explicit turn may legitimately end with a check question (pedagogy guardrail 1)."""
    if not arm_config:
        return {}
    out: dict[str, Any] = {"arm_intended": dict(arm_config)}
    if not completed:
        return out
    delivered = not arm_not_applied
    if arm_config.get("socratic") is True:
        delivered = delivered and socratic_delivered(text)
    rep = arm_config.get("representation")
    if rep and detected_representation is not None:
        delivered = delivered and detected_representation == rep
    out["arm_delivered"] = delivered
    if arm_not_applied:
        out["arm_not_applied"] = True
    return out


class TutorTurn:
    def __init__(
        self,
        db: AsyncSession,
        gateway: ModelGateway,
        repo: RetrievalRepository,
        *,
        quarantine_below_trust: int = QUARANTINE_BELOW_TRUST,
    ) -> None:
        self.db = db
        self.gateway = gateway
        self.repo = repo
        self.quarantine_below_trust = quarantine_below_trust

    @staticmethod
    def _contract(
        req: TurnRequest,
        action: actions.Action,
        *,
        hint_level: int,
        socratic: bool,
        representation: str | None,
        block_type: str,
        mastery: float,
    ) -> dict[str, Any]:
        contract = actions.output_contract(
            action,
            hint_level=hint_level,
            socratic=socratic,
            representation=representation,
            block_type=block_type,
            mastery=mastery,
        )
        if req.spoken and not req.conversation_lang:
            # read aloud (P9): brevity for the ear; citations stay in the written answer
            contract["max_sentences"] = min(int(contract["max_sentences"]), 4)
            contract["spoken"] = (
                "This answer is read aloud: at most 4 short sentences, no lists, no code blocks, "
                "no markdown; keep the source numbers in square brackets (they are shown, not spoken)."
            )
        if req.conversation_lang:
            # spoken practice (P9): the pedagogy base policy stays; the task instruction changes
            contract["instructions"] = prompts.voice_task("conversation").format(
                lang=req.conversation_lang
            )
            contract["max_sentences"] = 2
            contract["citation_format"] = "none (no sources in conversation practice)"
            contract["representation"] = "spoken reply"
        return contract

    async def run(self, req: TurnRequest) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        t0 = time.perf_counter()
        db = self.db
        session = await ksession.get(db, req.session_id)
        if session.ended_at:
            raise ValueError("session already ended")
        learner_id = session.learner_id
        checkpoint = await ksession.load_checkpoint(db, session.id) or {}

        conversation = bool(req.conversation_lang)
        if conversation:
            # spoken practice lives on the language node, never on an AI/ML skill (P9)
            node = await practice.vocab_deck(db, str(req.conversation_lang))
        elif req.skill_id:
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
        block_type = "recap" if action == actions.Action.SUMMARIZE else "new_material"
        turn_id = new_id()

        # a running node-unit experiment decides the questioning style / representation for this
        # node (matched-node design); disclosed on the session screen, stamped on every event
        socratic = session.socratic
        evidence = await tools.get_evidence(db, learner_id, node)
        mastery = float(evidence.get("mastery", 0.0))
        prefs = await tools.get_preferences(db, learner_id)
        allowed = set(representations.allowed_kinds(mastery))
        representation = req.representation
        detected: str | None = None
        if representation is None and prefs.get("tutor.representation_default"):
            # the accepted default (adaptation card) applies to skills not yet mastered only
            default_rep = str(prefs["tutor.representation_default"])
            if mastery < skill_graph.MASTERY_DONE and default_rep in allowed:
                representation = default_rep
        arm_pair = await experiments.arm_for_node(db, learner_id, node.id, session=session)
        experiment_arm_id: str | None = None
        arm_not_applied = False
        if arm_pair is not None:
            _, arm = arm_pair
            experiment_arm_id = arm.id
            if "socratic" in arm.config_json:
                socratic = bool(arm.config_json["socratic"])
            arm_rep = arm.config_json.get("representation")
            if arm_rep:
                if str(arm_rep) in allowed:
                    representation = str(arm_rep)
                else:  # never bypass the mastery gate (problem-first needs mastery ≥ 0.6)
                    arm_not_applied = True
        # arm fidelity (P2): the node arm, else the session's arm (session-unit experiments)
        arm_config: dict[str, Any] | None = dict(arm_pair[1].config_json) if arm_pair else None
        if arm_config is None and session.experiment_arm_id:
            session_arm = await db.get(ExperimentArm, session.experiment_arm_id)
            arm_config = dict(session_arm.config_json) if session_arm is not None else None

        activity = ACTIVITY_FOR_ACTION.get(action, ActivityType.NEW_MATERIAL)
        ctx = ksession.event_context(
            session,
            domain=Domain.LANGUAGE if conversation else Domain.AI_ML,
            activity=ActivityType.CHAT if conversation else activity,
        )
        if experiment_arm_id:
            ctx = dataclasses.replace(ctx, experiment_arm=experiment_arm_id)
        events = EventWriter(db, ctx)
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
                questioning_style="socratic" if socratic else "explicit",
                experiment_arm=experiment_arm_id,
                arm_not_applied=arm_not_applied,
            ).model_dump(),
        )

        if conversation:
            hits: list[Any] = []  # no course sources in conversation practice: nothing to cite
            rtrace_id: str | None = None
        else:
            result = await tools.retrieve(
                self.repo, f"{node.title}: {req.text}", skill_id=node.id, k=6
            )
            hits = list(result.hits)
            rtrace = await write_retrieval_trace(
                db,
                result.trace.model_copy(
                    update={"learner_id": learner_id, "session_id": session.id}
                ),
            )
            rtrace_id = rtrace.id
        packet = build_packet(
            policy=prompts.base_policy(),
            request=req.text,
            prompt_version=prompts.PROMPT_VERSION,
            preferences=prefs,
            session_state=tools.session_state(
                session, node, block_type=block_type, hint_level=hint_level, socratic=socratic
            ),
            learning_contract=await tools.get_learning_contract(db, node),
            evidence=evidence,
            retrieved=hits,
            quarantine_below_trust=self.quarantine_below_trust,
            output_contract=self._contract(
                req,
                action,
                hint_level=hint_level,
                socratic=socratic,
                representation=representation,
                block_type=block_type,
                mastery=mastery,
            ),
        )
        messages = render_messages(packet)

        handle = StreamHandle()
        text = ""
        completed = False
        stream = self.gateway.stream(
            TaskClass.CHAT_FAST if conversation else TASK_FOR_ACTION[action],
            messages,
            handle=handle,
            learner_id=learner_id,
            session_id=session.id,
            metadata={
                "prompt_version": prompts.PROMPT_VERSION,
                "skill_id": node.id,
                "turn_id": turn_id,
            },
            max_tokens=SOCRATIC_MAX_TOKENS if socratic else MAX_TOKENS_FOR_ACTION[action],
            events=events,
        )
        partial = False
        try:
            try:
                async for tok in stream:
                    text += tok
                    yield ("token", {"text": tok})
                completed = True
            except GatewayError:
                if not text:
                    raise  # nothing was said: the caller reports the failure
                partial = True  # the model stopped mid-way: keep what the learner has read
        finally:
            # close the model stream first so its model_call row exists before the trace links to it
            await stream.aclose()
            trimmed = actions.trim_incomplete_tail(text) if completed else text
            text = trimmed
            cited_idx = actions.cited_indices(text, len(packet.retrieved))
            sources = [
                SourceRef(
                    chunk_id=c.chunk_id,
                    citation=c.citation,
                    trust_tier=c.trust_tier,
                    score=c.score,
                    flagged=c.flagged,
                    cited=(i in cited_idx),
                )
                for i, c in enumerate(packet.retrieved, 1)
                if i in cited_idx or i <= 3
            ]
            cited_ids = [s.chunk_id for s in sources if s.cited]
            detected = actions.detect_representation(text)
            representation = detected
            sentences = actions.count_sentences(text)
            latency_ms = int((time.perf_counter() - t0) * 1000)
            trace = await write_tutor_trace(
                db,
                TutorTraceRecord(
                    learner_id=learner_id,
                    session_id=session.id,
                    turn_id=turn_id,
                    action=str(action) if completed else f"{action}:partial",
                    prompt_version=prompts.PROMPT_VERSION,
                    sections=packet.section_tokens,
                    dropped=packet.dropped,
                    model_call_id=handle.model_call_id,
                    retrieval_trace_id=rtrace_id,
                    latency_ms=latency_ms,
                ),
            )
            await events.emit(
                Verb.EXPLAINED,
                ObjectType.TURN,
                turn_id,
                actor=Actor.TUTOR,
                result={"sentences": sentences, "cited_sources": cited_ids},
                context={
                    "representation": representation,
                    "hint_count": hint_level,
                    "model": handle.registry_id,
                    "route": handle.route if completed else "partial",
                    "prompt_version": prompts.PROMPT_VERSION,
                    "latency_ms": latency_ms,
                    "tokens_in": handle.tokens_in,
                    "tokens_out": handle.tokens_out,
                    "cached_tokens": handle.cached_tokens,
                    "usage_source": handle.usage_source,
                    "cost_status": handle.cost_status,
                    "node_id": node.id,
                    "questioning_style": "socratic" if socratic else "explicit",
                    # arm fidelity (P2): what the experiment intended vs what this answer shows
                    **arm_fidelity(
                        arm_config,
                        text=text,
                        completed=completed,
                        arm_not_applied=arm_not_applied,
                        detected_representation=detected,
                    ),
                },
                representation=representation,
            )
            next_hint_level = 0 if action == actions.Action.FULL_SOLUTION else hint_level
            if not conversation:  # a chat in the language block never re-targets the AI/ML block
                await ksession.save_checkpoint(
                    db,
                    session,
                    {
                        **(cp_now := await ksession.load_checkpoint(db, session.id) or {}),
                        # the running new-material/challenge block owns the active skill; a question
                        # about another skill is answered but does not re-target the block
                        "skill_id": (
                            cp_now["skill_id"]
                            if cp_now.get("block_status") == "running"
                            and cp_now.get("block_type") in ("new_material", "challenge")
                            and cp_now.get("skill_id")
                            else node.id
                        ),
                        "hint_level": next_hint_level,
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
                outcome="partial" if partial else "ok",
                usage_source=handle.usage_source,
                cost_status=handle.cost_status,
                sentences=sentences,
                representation=representation,
                sources=sources,
                flagged=sorted({f for c in packet.retrieved for f in c.flagged}),
                dropped=packet.dropped,
                latency_ms=latency_ms,
                text=text,
            ).model_dump(),
        )
