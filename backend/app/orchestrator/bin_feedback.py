"""Deterministic, narrowly scoped bin feedback with saved-answer provenance."""

import logging
from dataclasses import asdict
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.answer_recovery import AnswerRecovery
from app.core.errors import AppError
from app.db.answers import save_completed
from app.db.base import new_id
from app.db.events import EventWriter, Verb
from app.db.traces import TutorTraceRecord, write_tutor_trace
from app.kernel import session as ksession
from app.kernel.bin_checks import VERSION as BIN_VERSION
from app.kernel.bin_checks import BinCheck
from app.orchestrator.feedback_render import literal
from app.orchestrator.workspace_checks import bin_summary
from app.schemas.common import ActivityType, ObjectType
from app.schemas.playground import PlaygroundReply, PlaygroundRequest

logger = logging.getLogger(__name__)


async def respond_bins(
    db: AsyncSession,
    learner_id: str,
    body: PlaygroundRequest,
    bins: list[BinCheck],
    version: str,
    *,
    recovery: AnswerRecovery | None = None,
) -> PlaygroundReply:
    session = await ksession.get(db, body.session_id)
    if session.learner_id != learner_id or session.ended_at:
        raise AppError("not_found", "Start or resume a session to use the tutor.", http_status=404)
    if not bins:
        raise ValueError("A supported bin check is required")
    parts = [
        "Code boundary check — your written answer has not been graded.",
        bin_summary(bins),
    ]
    for check in bins:
        if check.labels is not None:
            parts.append(f"Supplied labels for line {check.line} (not independently verified):")
            for index, label in enumerate(check.labels):
                quoted = "\n".join("> " + literal(line) for line in label.splitlines())
                parts.append(f"Bin {index + 1} label:\n\n{quoted}")
    parts.append(
        "With right=True, each bin includes its right edge; include_lowest=True also includes "
        "the first left edge. With right=False, bins include their left edges and exclude their "
        "right edges. Compare these intervals with the task's required intervals before deciding "
        "whether the code meets the requirement. Other claims in your answer have not been assessed. "
        "No code was executed and no dataset results or course requirements were verified."
    )
    if body.output_stale:
        parts.append(
            "The workspace client marks the supplied output as outdated; it does not verify "
            "the current code. To check current execution results, rerun the current cell."
        )
    text = "\n\n".join(parts)
    turn_id = new_id()
    events = EventWriter(db, ksession.event_context(session, activity=ActivityType.CHAT))
    await events.emit(
        Verb.ASKED, ObjectType.TURN, turn_id, context={"text_len": len(body.question)}
    )
    await write_tutor_trace(
        db,
        TutorTraceRecord(
            learner_id=learner_id,
            session_id=session.id,
            turn_id=turn_id,
            action="playground_" + body.intent,
            prompt_version=version,
            sections={"literal_bin_checks": len(bins)},
        ),
    )
    await events.emit(
        Verb.EXPLAINED,
        ObjectType.TURN,
        turn_id,
        result={"cited_sources": []},
        context={
            "representation": "playground_" + body.intent,
            "model": "none",
            "route": "deterministic",
            "prompt_version": version,
        },
    )
    snapshot: dict[str, Any] = dict(
        learner_id=learner_id,
        session_id=session.id,
        turn_id=turn_id,
        surface="playground",
        request=body.model_dump(exclude={"session_id"}),
        text=text,
        metadata={
            "model": "none",
            "route": "deterministic",
            "prompt_version": version,
            "sources": [],
            "feedback_scope": "literal_bin_boundaries_only",
            "bin_checks": [asdict(check) for check in bins],
            "bin_checker_version": BIN_VERSION,
            "execution_evidence_state": "stale_client_output"
            if body.output_stale
            else ("unverified_client_output" if body.output else "no_output"),
            "context_scope": "supplied_workspace_only",
            "learning_context": body.learning_context.model_dump()
            if body.learning_context
            else None,
        },
    )
    answer_id = save_error = save_receipt = None
    try:
        answer = await save_completed(db, **snapshot)
        answer_id = answer.id
    except SQLAlchemyError as exc:
        logger.warning("Bin feedback save failed: %s", type(exc).__name__)
        if recovery is not None:
            save_receipt = recovery.issue(snapshot)
        save_error = "This answer could not be saved to the database. Keep a copy before leaving."
    return PlaygroundReply(
        text=text,
        model="none",
        route="deterministic",
        turn_id=turn_id,
        answer_id=answer_id,
        save_error=save_error,
        save_receipt=save_receipt,
        source_note="Local code boundary check only; written answer not graded, code not executed.",
    )
