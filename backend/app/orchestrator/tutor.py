"""The one tutor loop (ADR-0007): interpret → identify skill → ContextPacket → retrieve → choose
action → stream generation → traces + events → checkpoint. Yields SSE-ready events.

A turn without a trace is a bug: the tutor_trace is written in a `finally`, also when the client
aborts the stream mid-way (the explanation is then flagged partial)."""

import asyncio
import dataclasses
import hashlib
import json
import logging
import re
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import httpx
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.answer_recovery import AnswerRecovery
from app.core.config import Settings
from app.core.tutor_timing import mark as timing_mark
from app.db.answers import save_completed
from app.db.base import new_id
from app.db.events import EventWriter, Verb
from app.db.lesson_answer_memory import retrieve as lesson_memory
from app.db.models import ExperimentArm
from app.db.traces import TutorTraceRecord, write_retrieval_trace, write_tutor_trace
from app.kernel import experiments, practice, representations, skill_graph
from app.kernel import session as ksession
from app.knowledge.repository import RetrievalRepository
from app.models_ai.gateway import GatewayError, ModelGateway, StreamHandle
from app.models_ai.provider import ProviderError, TaskClass
from app.models_ai.routing import NoModelReady
from app.orchestrator import (
    actions,
    assessment_help,
    lesson_semantic,
    literal_probe,
    personas,
    prompts,
    tools,
)
from app.orchestrator.context import (
    QUARANTINE_BELOW_TRUST,
    build_packet,
    quarantine,
    render_messages,
)
from app.orchestrator.socratic_lesson import stream_reply as stream_socratic_reply
from app.schemas.common import ActivityType, Actor, Domain, ObjectType
from app.schemas.tutor import SourceRef, TurnDone, TurnMeta, TurnRequest

logger = logging.getLogger(__name__)

MAX_TOKENS_FOR_ACTION = {  # Safety ceilings, not target answer lengths.
    actions.Action.EXPLAIN: 1600,
    actions.Action.HINT: 95,
    actions.Action.FULL_SOLUTION: 700,
    actions.Action.SUMMARIZE: 160,
}
SPOKEN_EXPLAIN_MAX_TOKENS = 190
# Thinking models count internal reasoning against this ceiling too.
# Brevity is a prompt/output contract, not a reason to truncate the final question.
SOCRATIC_MAX_TOKENS = 1600
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
        repo: RetrievalRepository | None,
        *,
        quarantine_below_trust: int = QUARANTINE_BELOW_TRUST,
        settings: Settings | None = None,
        recovery: AnswerRecovery | None = None,
        repo_loader: Callable[[], Awaitable[RetrievalRepository]] | None = None,
    ) -> None:
        self.settings = settings
        self.recovery = recovery
        self.db = db
        self.gateway = gateway
        self.repo = repo
        self.repo_loader = repo_loader
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
        lesson_discussion: bool = False,
    ) -> dict[str, Any]:
        contract = actions.output_contract(
            action,
            hint_level=hint_level,
            socratic=socratic,
            representation=representation,
            block_type=block_type,
            mastery=mastery,
        )
        if (
            action == actions.Action.EXPLAIN
            and socratic
            and lesson_discussion
            and not req.spoken
            and not req.conversation_lang
        ):
            contract.update(
                instructions=prompts.tutor_task("explain_socratic").strip(),
                response_kind="socratic_turn",
                max_sentences=3,
                shape_example=(
                    "Brief factual setup and exactly one unanswered narrowing question "
                    "in separate JSON fields."
                ),
                end_with="exactly one unanswered narrowing question",
            )
            if req.explanation_kind == "follow_up":
                contract.update(
                    instructions=prompts.tutor_task("explain_socratic_probe").strip(),
                    response_kind="socratic_follow_up",
                    probe_contract_version="socratic.probe.v2",
                    max_sentences=1,
                    shape_example=(
                        "Concrete situation and one focus in JSON; app renders one open question."
                    ),
                    scaffold="one_open_probe",
                    socratic_rule="one open question, no answer in its premise",
                    end_with="one open question rendered by the app",
                )
        if (
            action == actions.Action.EXPLAIN
            and req.explanation_kind == "follow_up"
            and lesson_discussion
            and not socratic
            and not req.conversation_lang
        ):
            contract.update(
                instructions=prompts.tutor_task("explain_followup").strip(),
                response_kind="follow_up",
                max_sentences=4,
                shape_example="Answer the specific question directly.",
                end_with="the requested result and reason; no extra practice task",
            )
            if not req.spoken and re.search(
                r"\b(why|causes?|because)\b|\bhow come\b", req.text, re.IGNORECASE
            ):
                contract.update(
                    instructions=prompts.tutor_task("explain_causal").strip(),
                    shape_example=("Input -> condition -> operation -> result. Immediate reason."),
                    end_with="the requested result and its immediate reason",
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
        timing_mark("turn_started")
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
            node = await skill_graph.get_node(db, req.skill_id, learner_id=learner_id)
        elif checkpoint.get("skill_id"):
            node = await skill_graph.get_node(db, checkpoint["skill_id"], learner_id=learner_id)
        else:
            nxt = await skill_graph.next_skill(db, learner_id)
            if nxt is None:
                raise ValueError("no skills seeded")
            node = nxt
        checked_assessment = None
        if req.assessment_answer_id is not None:
            if conversation:
                raise ValueError("Assessment help is unavailable in conversation mode")
            checked_assessment = await assessment_help.load_context(
                db,
                answer_id=req.assessment_answer_id,
                learner_id=learner_id,
                session_id=session.id,
                skill_id=node.id,
            )
        prev_hint = (
            int(checkpoint.get("hint_level", 0)) if checkpoint.get("skill_id") == node.id else 0
        )
        action, hint_level = actions.choose_action(req.text, req.action, prev_hint)
        block_type = "recap" if action == actions.Action.SUMMARIZE else "new_material"
        turn_id = new_id()

        # a running node-unit experiment decides the questioning style / representation for this
        # node (matched-node design); disclosed on the session screen, stamped on every event
        socratic = session.socratic
        timing_mark("evidence_started")
        evidence = await tools.get_evidence(db, learner_id, node)
        mastery = float(evidence.get("mastery", 0.0))
        prefs = await tools.get_preferences(db, learner_id)
        presentation = personas.from_preferences(prefs)
        presentation_version = prompts.PROMPT_VERSION + presentation.suffix
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
                prompt_version=presentation_version,
                questioning_style="socratic" if socratic else "explicit",
                experiment_arm=experiment_arm_id,
                arm_not_applied=arm_not_applied,
            ).model_dump(),
        )

        probe = (
            literal_probe.from_request(req.text, language=presentation.language)
            if (
                action == actions.Action.EXPLAIN
                and socratic
                and req.explanation_kind == "follow_up"
                and not req.spoken
                and not conversation
                and checked_assessment is None
                and checkpoint.get("phase") == "teach"
            )
            else None
        )
        learning_contract = await tools.get_learning_contract(db, node, learner_id=learner_id)
        retrieval_query = "\n".join(
            [
                node.title,
                str(learning_contract.get("objective", "")),
                str(learning_contract.get("success_criteria", "")),
                req.text,
            ]
        )
        timing_mark("retrieval_started")
        if conversation or probe is not None:
            hits: list[Any] = []  # no course sources in conversation practice: nothing to cite
            rtrace_id: str | None = None
        else:
            if self.repo is None:
                if self.repo_loader is None:
                    raise RuntimeError("Retrieval repository is not configured")
                self.repo = await self.repo_loader()
            result = await tools.retrieve(
                self.repo,
                retrieval_query,
                skill_id=node.id,
                course=node.course,
                k=6,
                anchors=await tools.lesson_sources(db, node, learner_id=learner_id),
            )
            hits = list(result.hits)
            rtrace = await write_retrieval_trace(
                db,
                result.trace.model_copy(
                    update={"learner_id": learner_id, "session_id": session.id}
                ),
            )
            rtrace_id = rtrace.id
        timing_mark("retrieval_finished")
        teaching_contract = self._contract(
            req,
            action,
            hint_level=hint_level,
            socratic=socratic,
            representation=representation,
            block_type=block_type,
            mastery=mastery,
            lesson_discussion=checkpoint.get("phase") == "teach" and checked_assessment is None,
        )
        if not conversation and not quarantine(hits, [], below_trust=self.quarantine_below_trust):
            teaching_contract["citation_format"] = (
                "No numbered sources were supplied. Do not use numeric citation markers; "
                "say no course source for this."
            )
        if checked_assessment is not None:
            teaching_contract = {
                **teaching_contract,
                "checked_assessment_answer_id": req.assessment_answer_id,
            }
        contract_key = hashlib.sha256(
            json.dumps([presentation_version, teaching_contract], sort_keys=True).encode()
        ).hexdigest()
        timing_mark("literal_history_started")
        historical = []
        # A fresh Socratic question must come from the current lesson, not a copied
        # previous question or an unverified tutor explanation. History remains readable.
        fresh_socratic = teaching_contract.get("response_kind") in {
            "socratic_turn",
            "socratic_follow_up",
        }
        if not conversation and not fresh_socratic:
            try:
                async with db.begin_nested():
                    historical = await lesson_memory(
                        db,
                        learner_id,
                        node.id,
                        req.text,
                        str(action),
                        "socratic" if socratic else "explicit",
                        contract_key,
                    )
            except SQLAlchemyError as exc:
                logger.warning("Lesson answer lookup unavailable: %s", type(exc).__name__)
        timing_mark("literal_history_finished")
        if (
            not conversation
            and not fresh_socratic
            and self.settings is not None
            and len(historical) < 2
        ):
            timing_mark("semantic_history_started")
            node_id = node.id
            related: list[dict[str, str]] = []
            try:
                related = await asyncio.wait_for(
                    lesson_semantic.retrieve(
                        db,
                        self.settings,
                        learner_id,
                        node_id,
                        req.text,
                        str(action),
                        "socratic" if socratic else "explicit",
                        contract_key,
                    ),
                    timeout=2.0,
                )
            except (
                SQLAlchemyError,
                httpx.HTTPError,
                ValueError,
                ProviderError,
                NoModelReady,
                TimeoutError,
            ) as exc:
                await db.rollback()
                logger.warning("Lesson semantic lookup unavailable: %s", type(exc).__name__)
                session = await ksession.get(db, req.session_id)
                node = await skill_graph.get_node(db, node_id, learner_id=learner_id)
            # Literal candidates may have been reported/changed during semantic inference.
            historical = []
            try:
                async with db.begin_nested():
                    historical = await lesson_memory(
                        db,
                        learner_id,
                        node_id,
                        req.text,
                        str(action),
                        "socratic" if socratic else "explicit",
                        contract_key,
                    )
            except SQLAlchemyError as exc:
                logger.warning("Lesson history recheck unavailable: %s", type(exc).__name__)
            seen = {item["answer_id"] for item in historical}
            historical = (historical + [item for item in related if item["answer_id"] not in seen])[
                :2
            ]
        timing_mark("context_started")
        packet = build_packet(
            policy=prompts.base_policy() + presentation.instruction,
            historical=historical,
            checked_assessment=checked_assessment,
            request=req.text,
            prompt_version=presentation_version,
            preferences=prefs,
            session_state=tools.session_state(
                session, node, block_type=block_type, hint_level=hint_level, socratic=socratic
            ),
            learning_contract=learning_contract,
            evidence=evidence,
            retrieved=hits,
            quarantine_below_trust=self.quarantine_below_trust,
            output_contract=teaching_contract,
        )
        messages = render_messages(packet)

        timing_mark("context_finished")
        handle = StreamHandle()
        text = ""
        completed = False
        max_tokens = (
            SOCRATIC_MAX_TOKENS
            if socratic
            else SPOKEN_EXPLAIN_MAX_TOKENS
            if (req.spoken or conversation) and action == actions.Action.EXPLAIN
            else MAX_TOKENS_FOR_ACTION[action]
        )
        generation_metadata = {
            "prompt_version": presentation_version,
            "skill_id": node.id,
            "tutor_presentation": {
                "persona": presentation.persona,
                "language": presentation.language,
            },
            "turn_id": turn_id,
        }
        if "probe_contract_version" in teaching_contract:
            generation_metadata["probe_contract_version"] = teaching_contract[
                "probe_contract_version"
            ]
        if probe is not None:
            stream = literal_probe.stream(
                probe, handle, language="de" if presentation.language == "de" else "en"
            )
        elif fresh_socratic:
            stream = stream_socratic_reply(
                self.gateway,
                messages,
                handle=handle,
                learner_id=learner_id,
                session_id=session.id,
                metadata=generation_metadata,
                max_tokens=max_tokens,
                events=events,
                question_only=teaching_contract.get("response_kind") == "socratic_follow_up",
            )
        else:
            stream = self.gateway.stream(
                TaskClass.CHAT_FAST if conversation else TASK_FOR_ACTION[action],
                messages,
                handle=handle,
                learner_id=learner_id,
                session_id=session.id,
                metadata=generation_metadata,
                max_tokens=max_tokens,
                events=events,
            )
        partial = False
        try:
            try:
                async for tok in stream:
                    if tok:
                        timing_mark("first_text_ready")
                    text += tok
                    yield ("token", {"text": tok})
                partial = handle.finish_reason == "length"
                completed = not partial
            except GatewayError:
                if not text:
                    raise  # nothing was said: the caller reports the failure
                partial = True  # the model stopped mid-way: keep what the learner has read
        finally:
            # close the model stream first so its model_call row exists before the trace links to it
            await stream.aclose()
            timing_mark("generation_closed")
            # Keep the actual model output. A normal stop may end with a code fence,
            # equation or list; sentence heuristics must never delete its tail.
            # Length/error interruptions are already disclosed through outcome=partial.
            citation_flags = (
                ["unsupported_numeric_citation"]
                if actions.has_unsupported_citation(text, len(packet.retrieved))
                else []
            )
            if (
                completed
                and socratic
                and not conversation
                and action == actions.Action.EXPLAIN
                and actions.has_socratic_format_mismatch(text)
            ):
                citation_flags.append("socratic_format_mismatch")
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
                    prompt_version=presentation_version,
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
                    "prompt_version": presentation_version,
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

        answer_id = None
        save_error = None
        save_receipt = None
        trace_id = trace.id
        if completed and text.strip():
            snapshot: dict[str, Any] = dict(
                learner_id=learner_id,
                session_id=session.id,
                turn_id=turn_id,
                surface="tutor",
                request=req.model_dump(exclude={"session_id"}),
                text=text,
                metadata={
                    "skill_id": node.id,
                    "teaching_action": str(action),
                    "teaching_contract_key": contract_key,
                    "tutor_presentation": {
                        "persona": presentation.persona,
                        "language": presentation.language,
                    },
                    "memory_context_version": "lesson.v1",
                    "answer_memory": packet.historical,
                    "area_id": node.area_id,
                    "course_label": node.course,
                    "model": handle.registry_id,
                    "route": handle.route,
                    "generation_kind": literal_probe.VERSION if probe is not None else "model",
                    "prompt_version": presentation_version,
                    "model_call_id": handle.model_call_id,
                    "questioning_style": "socratic" if socratic else "explicit",
                    "socratic_format_checked": (
                        socratic and not conversation and action == actions.Action.EXPLAIN
                    ),
                    "sources": [source.model_dump() for source in sources],
                    "flagged": sorted(
                        {f for c in packet.retrieved for f in c.flagged} | set(citation_flags)
                    ),
                    "source_text_hashes": {
                        c.chunk_id: hashlib.sha256(c.text.encode()).hexdigest()
                        for c in packet.retrieved
                    },
                    "dropped": packet.dropped,
                },
            )
            try:
                answer = await save_completed(db, **snapshot)
                answer_id = answer.id
            except SQLAlchemyError as exc:
                logger.warning("Tutor answer save failed: %s", type(exc).__name__)
                if self.recovery is not None:
                    save_receipt = self.recovery.issue(snapshot)
                save_error = (
                    "This answer could not be saved to the database. Keep a copy before leaving."
                )

        timing_mark("answer_finalized")
        yield (
            "done",
            TurnDone(
                turn_id=turn_id,
                answer_id=answer_id,
                memory_answers=[item["answer_id"] for item in packet.historical],
                save_error=save_error,
                save_receipt=save_receipt,
                model_call_id=handle.model_call_id,
                tutor_trace_id=trace_id,
                registry_id=handle.registry_id,
                route=handle.route,
                outcome="partial" if partial else "ok",
                usage_source=handle.usage_source,
                cost_status=handle.cost_status,
                sentences=sentences,
                representation=representation,
                sources=sources,
                flagged=sorted(
                    {f for c in packet.retrieved for f in c.flagged} | set(citation_flags)
                ),
                dropped=packet.dropped,
                latency_ms=latency_ms,
                text=text,
            ).model_dump(),
        )
