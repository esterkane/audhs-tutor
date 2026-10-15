"""Resolve bounded learner notes without turning them into verified evidence."""

from typing import Any

from pydantic import ValidationError

from app.db.models import TutorAnswer
from app.orchestrator.answer_check_binding import text_hash
from app.schemas.ask import ConversationBrief


def resolve(supplied: ConversationBrief | None, parent: TutorAnswer | None) -> dict[str, Any]:
    mode = "supplied"
    brief = supplied
    if brief is None and parent is not None:
        raw = parent.metadata_json.get("conversation_brief")
        if raw is not None:
            if (
                isinstance(raw, dict)
                and raw.get("mode") in {"absent", "unavailable"}
                and raw.get("value") is None
            ):
                return {"mode": raw["mode"], "value": None}
            if (
                not isinstance(raw, dict)
                or raw.get("mode") not in {"supplied", "inherited", "cleared"}
                or raw.get("origin") != "learner_supplied_unverified"
                or not isinstance(raw.get("value"), dict)
                or set(raw["value"]) != {"version", "task", "notes", "examples", "unresolved"}
            ):
                return {"mode": "unavailable", "value": None}
            try:
                brief = ConversationBrief.model_validate(raw["value"])
            except ValidationError:
                return {"mode": "unavailable", "value": None}
            if raw.get("hash") != text_hash(brief.model_dump_json()):
                return {"mode": "unavailable", "value": None}
            mode = "inherited"
    if brief is None:
        return {"mode": "absent", "value": None}
    value = brief.model_dump(mode="json")
    if not any(value[field].strip() for field in ("task", "notes", "examples", "unresolved")):
        mode = "cleared"
    return {
        "mode": mode,
        "value": value,
        "hash": text_hash(brief.model_dump_json()),
        "origin": "learner_supplied_unverified",
        "parent_answer_id": parent.id if parent is not None and supplied is None else None,
    }
