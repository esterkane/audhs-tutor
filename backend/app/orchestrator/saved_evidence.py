"""Verified local reuse of explicitly identified saved retry observations."""

import re
from dataclasses import dataclass
from typing import Any

from app.integrations.supabase_evidence import retry_report, stored_experiments
from app.kernel.evidence_answers import UnsupportedPlan
from app.orchestrator.saved_evidence_frame import supported_fact_frame
from app.orchestrator.saved_evidence_selection import source_choices


@dataclass(frozen=True)
class SavedEvidenceAnswer:
    text: str
    record_ids: tuple[str, ...]
    revisions: tuple[str, ...]
    method: str = "literal-reference-proof.v1"


def _last_declared(history: list[dict[str, Any]]) -> int:
    return len(
        {
            block["id"]
            for message in history
            if message.get("role") == "assistant" and isinstance(message.get("content"), list)
            for block in message["content"]
            if isinstance(block, dict)
            and block.get("type") == "tool_use"
            and block.get("name") == "compare_isolation_lab"
            and isinstance(block.get("id"), str)
        }
    )


async def answer_saved_retry(
    question: str, state: Any, history: list[dict[str, Any]], client: Any = None
) -> SavedEvidenceAnswer | None:
    if (
        state.mode != "neutral"
        or state.delivery != "explicit"
        or state.incident is not None
        or getattr(state, "active_lab", None) is not None
    ):
        return None
    if not re.search(r"retry|retries|wiederhol", question, re.I) or not re.search(
        r"saved|stored|recorded|experiment|trial|gespeichert|versuch", question, re.I
    ):
        return None
    if not supported_fact_frame(question):
        return None
    records = stored_experiments(history)
    if not records:
        return None
    chosen = source_choices(question, records, last_ordinal=_last_declared(history))
    if chosen is None:
        return None
    try:
        text = retry_report(records, chosen, language=state.language)
    except UnsupportedPlan:
        return None
    revisions = {record.source.id: record.source.revision for record in records}
    return SavedEvidenceAnswer(
        text, tuple(chosen), tuple(revisions[identity] for identity in chosen)
    )
