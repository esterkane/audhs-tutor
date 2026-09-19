"""Learning-event writer (docs/EVENT-SCHEMA.md). Append-only; verbs are a closed enum.

`EventWriter.emit()` fills ts/ULID/mode/energy/socratic/experiment_arm from the bound
`EventContext`, validates payload keys against the schema table below and never updates rows.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LearningEvent
from app.schemas.common import ActivityType, Actor, Domain, Modality, Mode, ObjectType


class Verb(StrEnum):
    STARTED = "started"
    ENDED = "ended"
    BLOCK_STARTED = "block_started"
    BLOCK_ENDED = "block_ended"
    ASKED = "asked"
    EXPLAINED = "explained"
    PREFERRED = "preferred"
    ATTEMPTED = "attempted"
    GRADED = "graded"
    EVIDENCED = "evidenced"
    PROPOSED = "proposed"
    DECIDED = "decided"
    REVIEWED = "reviewed"
    ADAPTED = "adapted"
    UNDONE = "undone"
    PARKED = "parked"
    PROMOTED = "promoted"
    SPOKE = "spoke"
    PRACTICED = "practiced"
    ASSIGNED = "assigned"
    MEASURED = "measured"
    DEGRADED = "degraded"
    INVALID_OUTPUT = "invalid_output"


# verb -> (allowed result keys, allowed context keys). Adding a key = edit EVENT-SCHEMA.md too.
_R = frozenset
PAYLOAD_KEYS: dict[Verb, tuple[frozenset[str], frozenset[str]]] = {
    Verb.STARTED: (_R({"energy_after", "self_report", "notes"}), _R({"planned_blocks"})),
    Verb.ENDED: (_R({"energy_after", "self_report", "notes"}), _R({"planned_blocks"})),
    Verb.BLOCK_STARTED: (
        _R({"actual_min", "switched_early", "reason"}),
        _R({"block_type", "planned_min", "node_ids"}),
    ),
    Verb.BLOCK_ENDED: (
        _R({"actual_min", "switched_early", "reason"}),
        _R({"block_type", "planned_min", "node_ids"}),
    ),
    Verb.ASKED: (_R(), _R({"text_len", "node_id"})),
    Verb.EXPLAINED: (
        _R({"sentences", "cited_sources"}),
        _R(
            {
                "representation",
                "hint_count",
                "model",
                "route",
                "prompt_version",
                "latency_ms",
                "tokens_in",
                "tokens_out",
                "cached_tokens",
            }
        ),
    ),
    Verb.PREFERRED: (
        _R({"chosen_id", "rejected_id", "reason"}),
        _R({"representation_chosen", "representation_rejected"}),
    ),
    Verb.ATTEMPTED: (
        _R({"correct", "confidence_pre", "latency_ms", "hint_count", "answer_len"}),
        _R({"item_type", "node_id"}),
    ),
    Verb.GRADED: (
        _R({"criterion_results", "score", "misconception", "confidence", "feedback_len"}),
        _R({"grader_level", "prompt_version", "rubric_version"}),
    ),
    Verb.EVIDENCED: (_R({"skill_id", "dimension", "score", "weight"}), _R({"attempt_id"})),
    Verb.PROPOSED: (_R({"decision"}), _R({"what", "why", "origin"})),
    Verb.DECIDED: (_R({"decision"}), _R({"what", "why", "origin"})),
    Verb.REVIEWED: (
        _R(
            {
                "rating",
                "latency_ms",
                "predicted_retrievability",
                "days_since_learned",
                "stability_before",
                "stability_after",
            }
        ),
        _R({"item_type", "node_id"}),
    ),
    Verb.ADAPTED: (_R(), _R({"what", "why", "reversible", "policy_version"})),
    Verb.UNDONE: (_R(), _R({"what", "why", "reversible", "policy_version"})),
    Verb.PARKED: (_R(), _R({"node_id", "promoted_to"})),
    Verb.PROMOTED: (_R(), _R({"node_id", "promoted_to"})),
    Verb.SPOKE: (
        _R({"stt_ms", "llm_first_token_ms", "tts_first_audio_ms", "total_ms"}),
        _R({"stt_model", "tts_model", "lang"}),
    ),
    Verb.PRACTICED: (_R({"duration_min", "self_rating"}), _R({"domain", "activity", "notes"})),
    Verb.ASSIGNED: (_R({"arm", "metric", "value", "n"}), _R({"experiment_id"})),
    Verb.MEASURED: (_R({"arm", "metric", "value", "n"}), _R({"experiment_id"})),
    Verb.DEGRADED: (_R(), _R({"from_alias", "to_alias", "reason"})),
    Verb.INVALID_OUTPUT: (_R(), _R({"task", "model", "attempts"})),
}


class EventPayloadError(ValueError):
    pass


@dataclass(frozen=True)
class EventContext:
    """Session-level facts stamped on every event. Built once per session/turn by the kernel."""

    learner_id: str
    session_id: str | None
    mode: Mode
    energy: int
    socratic: bool = False
    experiment_arm: str | None = None
    domain: Domain = Domain.META
    activity_type: ActivityType = ActivityType.CHAT
    modality: Modality = Modality.TEXT


def validate_payload(
    verb: Verb, result: dict[str, Any] | None, context: dict[str, Any] | None
) -> None:
    allowed_result, allowed_context = PAYLOAD_KEYS[verb]
    for label, payload, allowed in (
        ("result", result, allowed_result),
        ("context", context, allowed_context),
    ):
        if payload:
            extra = set(payload) - allowed
            if extra:
                raise EventPayloadError(
                    f"{verb}: undocumented {label} keys {sorted(extra)} — update EVENT-SCHEMA.md"
                )


class EventWriter:
    def __init__(self, db: AsyncSession, ctx: EventContext) -> None:
        self._db = db
        self.ctx = ctx

    async def emit(
        self,
        verb: Verb,
        object_type: ObjectType,
        object_id: str,
        *,
        actor: Actor = Actor.LEARNER,
        result: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        representation: str | None = None,
        commit: bool = True,
    ) -> LearningEvent:
        validate_payload(verb, result, context)
        c = self.ctx
        ev = LearningEvent(
            learner_id=c.learner_id,
            session_id=c.session_id,
            actor=str(actor),
            verb=str(verb),
            object_type=str(object_type),
            object_id=object_id,
            domain=str(c.domain),
            activity_type=str(c.activity_type),
            representation=representation,
            modality=str(c.modality),
            mode=str(c.mode),
            energy=c.energy,
            socratic=c.socratic,
            experiment_arm=c.experiment_arm,
            result_json=result,
            context_json=context,
        )
        self._db.add(ev)
        if commit:
            await self._db.commit()
        else:
            await self._db.flush()
        return ev
