"""SQLAlchemy 2 ORM for every Phase-1 table (docs/ARCHITECTURE.md §4).

Conventions: ULID ids, UTC ISO-8601 text timestamps, `learner_id` on every learner-scoped table,
JSON payloads in `*_json` columns. Curriculum/knowledge/model tables are shared (no learner_id).
"""

from typing import Any

from sqlalchemy import (
    DDL,
    JSON,
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, new_id, utcnow_iso
from app.db.ddl import LEARNING_EVENT_GUARDS

JsonDict = dict[str, Any]
JsonList = list[Any]


class IdMixin:
    id: Mapped[str] = mapped_column(Text, primary_key=True, default=new_id)


class LearnerScoped:
    learner_id: Mapped[str] = mapped_column(Text, ForeignKey("learner_profile.id"), index=True)


# ---------------------------------------------------------------- learner
class LearnerProfile(IdMixin, Base):
    __tablename__ = "learner_profile"
    display_name: Mapped[str] = mapped_column(Text)
    settings_json: Mapped[JsonDict] = mapped_column(JSON, default=dict)
    created_at: Mapped[str] = mapped_column(Text, default=utcnow_iso)


class LearnerPreference(IdMixin, LearnerScoped, Base):
    __tablename__ = "learner_preference"
    __table_args__ = (UniqueConstraint("learner_id", "key", name="uq_learner_preference_key"),)
    key: Mapped[str] = mapped_column(Text)
    value_json: Mapped[Any] = mapped_column(JSON)
    origin: Mapped[str] = mapped_column(Text)  # explicit | proposed_accepted | inferred
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    reversible: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[str] = mapped_column(Text, default=utcnow_iso, onupdate=utcnow_iso)


class Session(IdMixin, LearnerScoped, Base):
    __tablename__ = "session"
    started_at: Mapped[str] = mapped_column(Text, default=utcnow_iso)
    ended_at: Mapped[str | None] = mapped_column(Text)
    mode: Mapped[str] = mapped_column(Text)  # novelty | steady | low_capacity
    energy: Mapped[int] = mapped_column(Integer)  # 1-5
    socratic: Mapped[bool] = mapped_column(Boolean, default=False)
    energy_after: Mapped[int | None] = mapped_column(Integer)
    planned_blocks_json: Mapped[JsonList] = mapped_column(JSON, default=list)
    experiment_arm_id: Mapped[str | None] = mapped_column(Text)  # session-unit n-of-1 assignment


class SessionCheckpoint(IdMixin, LearnerScoped, Base):
    __tablename__ = "session_checkpoint"
    session_id: Mapped[str] = mapped_column(Text, ForeignKey("session.id"), index=True)
    packet_json: Mapped[JsonDict] = mapped_column(JSON)
    ts: Mapped[str] = mapped_column(Text, default=utcnow_iso)
    expires_at: Mapped[str] = mapped_column(Text)


# ---------------------------------------------------------------- curriculum (shared)
class SkillNode(IdMixin, Base):
    __tablename__ = "skill_node"
    domain: Mapped[str] = mapped_column(Text, index=True)
    course: Mapped[str | None] = mapped_column(Text, index=True)  # published-from course (P4 goal)
    slug: Mapped[str] = mapped_column(Text, unique=True)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="")
    success_criteria_json: Mapped[JsonList] = mapped_column(JSON, default=list)
    assessment_requirements_json: Mapped[JsonDict] = mapped_column(JSON, default=dict)
    example_applications_json: Mapped[JsonList] = mapped_column(JSON, default=list)
    created_at: Mapped[str] = mapped_column(Text, default=utcnow_iso)


class SkillEdge(IdMixin, Base):
    __tablename__ = "skill_edge"
    __table_args__ = (
        UniqueConstraint("from_skill_id", "to_skill_id", "kind", name="uq_skill_edge"),
    )
    from_skill_id: Mapped[str] = mapped_column(Text, ForeignKey("skill_node.id"), index=True)
    to_skill_id: Mapped[str] = mapped_column(Text, ForeignKey("skill_node.id"), index=True)
    kind: Mapped[str] = mapped_column(Text, default="prerequisite")  # prerequisite | related
    weight: Mapped[float] = mapped_column(Float, default=1.0)


class LearningObject(IdMixin, Base):
    __tablename__ = "learning_object"
    skill_id: Mapped[str] = mapped_column(Text, ForeignKey("skill_node.id"), index=True)
    concept: Mapped[str] = mapped_column(Text)
    goal: Mapped[str] = mapped_column(Text)
    sources_json: Mapped[JsonList] = mapped_column(JSON, default=list)
    examples_json: Mapped[JsonList] = mapped_column(JSON, default=list)
    exercises_json: Mapped[JsonList] = mapped_column(JSON, default=list)
    success_criteria_json: Mapped[JsonList] = mapped_column(JSON, default=list)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str] = mapped_column(Text, default=utcnow_iso)


class Representation(IdMixin, Base):
    __tablename__ = "representation"
    object_id: Mapped[str] = mapped_column(Text, ForeignKey("learning_object.id"), index=True)
    kind: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    model_call_id: Mapped[str | None] = mapped_column(Text, ForeignKey("model_call.id"))
    cached: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[str] = mapped_column(Text, default=utcnow_iso)


# ---------------------------------------------------------------- competence & memory
class CompetencyEvidence(IdMixin, LearnerScoped, Base):
    __tablename__ = "competency_evidence"
    skill_id: Mapped[str] = mapped_column(Text, ForeignKey("skill_node.id"), index=True)
    dimension: Mapped[str] = mapped_column(Text)  # recall | explanation | application | transfer
    score: Mapped[float] = mapped_column(Float)  # 0-1
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    grader_level: Mapped[str] = mapped_column(Text, default="deterministic")
    source_attempt_id: Mapped[str | None] = mapped_column(Text, ForeignKey("assessment_attempt.id"))
    ts: Mapped[str] = mapped_column(Text, default=utcnow_iso)


class CompetencyState(IdMixin, LearnerScoped, Base):
    """Materialized view; written only by kernel/competency.refresh()."""

    __tablename__ = "competency_state"
    __table_args__ = (
        UniqueConstraint("learner_id", "skill_id", "dimension", name="uq_competency_state"),
    )
    skill_id: Mapped[str] = mapped_column(Text, ForeignKey("skill_node.id"), index=True)
    dimension: Mapped[str] = mapped_column(Text)
    score: Mapped[float] = mapped_column(Float)
    count: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Float)
    last_evidence_ts: Mapped[str | None] = mapped_column(Text)
    refreshed_at: Mapped[str] = mapped_column(Text, default=utcnow_iso)


class ReviewItem(IdMixin, LearnerScoped, Base):
    __tablename__ = "review_item"
    skill_id: Mapped[str] = mapped_column(Text, ForeignKey("skill_node.id"), index=True)
    object_id: Mapped[str | None] = mapped_column(Text, ForeignKey("learning_object.id"))
    item_type: Mapped[str] = mapped_column(Text)
    prompt_json: Mapped[JsonDict] = mapped_column(JSON)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[str] = mapped_column(Text, default=utcnow_iso)


class MemoryState(IdMixin, LearnerScoped, Base):
    """FSRS card state; written only by the FSRS scheduler."""

    __tablename__ = "memory_state"
    review_item_id: Mapped[str] = mapped_column(Text, ForeignKey("review_item.id"), unique=True)
    fsrs_card_json: Mapped[JsonDict] = mapped_column(JSON)
    stability: Mapped[float | None] = mapped_column(Float)
    difficulty: Mapped[float | None] = mapped_column(Float)
    state: Mapped[str] = mapped_column(Text, default="new")
    due: Mapped[str] = mapped_column(Text, index=True)
    last_review: Mapped[str | None] = mapped_column(Text)


class ReviewLog(IdMixin, LearnerScoped, Base):
    __tablename__ = "review_log"
    review_item_id: Mapped[str] = mapped_column(Text, ForeignKey("review_item.id"), index=True)
    rating: Mapped[int] = mapped_column(Integer)  # 1-4
    reviewed_at: Mapped[str] = mapped_column(Text, default=utcnow_iso)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    predicted_retrievability: Mapped[float | None] = mapped_column(Float)
    fsrs_log_json: Mapped[JsonDict] = mapped_column(JSON, default=dict)


# ---------------------------------------------------------------- assessment
class AssessmentRubric(IdMixin, Base):
    __tablename__ = "assessment_rubric"
    criteria_json: Mapped[JsonList] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str] = mapped_column(Text, default=utcnow_iso)


class Assessment(IdMixin, Base):
    __tablename__ = "assessment"
    skill_id: Mapped[str] = mapped_column(Text, ForeignKey("skill_node.id"), index=True)
    kind: Mapped[str] = mapped_column(Text)  # mcq | cloze | explain_back | code | transfer
    item_json: Mapped[JsonDict] = mapped_column(JSON)
    rubric_id: Mapped[str | None] = mapped_column(Text, ForeignKey("assessment_rubric.id"))
    created_at: Mapped[str] = mapped_column(Text, default=utcnow_iso)


class AssessmentAttempt(IdMixin, LearnerScoped, Base):
    __tablename__ = "assessment_attempt"
    assessment_id: Mapped[str] = mapped_column(Text, ForeignKey("assessment.id"), index=True)
    session_id: Mapped[str | None] = mapped_column(Text, ForeignKey("session.id"))
    answer: Mapped[str] = mapped_column(Text)
    confidence_pre: Mapped[int | None] = mapped_column(Integer)
    deterministic_result_json: Mapped[JsonDict | None] = mapped_column(JSON)
    llm_result_json: Mapped[JsonDict | None] = mapped_column(JSON)
    grader_route: Mapped[str | None] = mapped_column(Text)
    correct: Mapped[bool | None] = mapped_column(Boolean)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    hint_count: Mapped[int] = mapped_column(Integer, default=0)
    ts: Mapped[str] = mapped_column(Text, default=utcnow_iso)


# ---------------------------------------------------------------- knowledge (shared)
class Document(IdMixin, Base):
    __tablename__ = "document"
    title: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(
        Text
    )  # udemy_caption | slides | notebook | pdf | markdown | manual
    uri: Mapped[str] = mapped_column(Text, default="")
    course: Mapped[str | None] = mapped_column(Text, index=True)
    section: Mapped[str | None] = mapped_column(Text)
    lecture: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, default=utcnow_iso)


class DocumentVersion(IdMixin, Base):
    __tablename__ = "document_version"
    __table_args__ = (
        UniqueConstraint("document_id", "content_hash", name="uq_document_version_hash"),
    )
    document_id: Mapped[str] = mapped_column(Text, ForeignKey("document.id"), index=True)
    content_hash: Mapped[str] = mapped_column(Text, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    publication_date: Mapped[str | None] = mapped_column(Text)
    ingested_at: Mapped[str] = mapped_column(Text, default=utcnow_iso)


class Chunk(IdMixin, Base):
    __tablename__ = "chunk"
    document_version_id: Mapped[str] = mapped_column(
        Text, ForeignKey("document_version.id"), index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    t_start: Mapped[float | None] = mapped_column(Float)
    t_end: Mapped[float | None] = mapped_column(Float)
    skill_ids_json: Mapped[JsonList] = mapped_column(JSON, default=list)
    norm_hash: Mapped[str | None] = mapped_column(Text, index=True)  # dedupe key (normalised text)
    # duplicate of another chunk in the same course: stored (system of record), never indexed
    duplicate_of: Mapped[str | None] = mapped_column(
        Text, ForeignKey("chunk.id", name="fk_chunk_duplicate_of"), index=True
    )


class ChunkProvenance(IdMixin, Base):
    __tablename__ = "chunk_provenance"
    chunk_id: Mapped[str] = mapped_column(Text, ForeignKey("chunk.id"), unique=True)
    source_id: Mapped[str] = mapped_column(Text, index=True)
    path: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(Text)
    trust_tier: Mapped[int] = mapped_column(Integer, default=2)  # 0 untrusted … 3 owner-verified
    course: Mapped[str | None] = mapped_column(Text)
    section: Mapped[str | None] = mapped_column(Text)
    lecture: Mapped[str | None] = mapped_column(Text)
    ingested_at: Mapped[str] = mapped_column(Text, default=utcnow_iso)
    flags_json: Mapped[JsonList] = mapped_column(JSON, default=list)  # instruction patterns found


class IndexState(IdMixin, Base):
    __tablename__ = "index_state"
    collection: Mapped[str] = mapped_column(Text, unique=True)
    embedding_registry_id: Mapped[str] = mapped_column(Text)
    embedding_version: Mapped[int] = mapped_column(Integer)
    dims: Mapped[int] = mapped_column(Integer)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    last_reindex: Mapped[str | None] = mapped_column(Text)


# ---------------------------------------------------------------- models (shared)
class ModelRegistry(Base):
    """ADR-0010. `id` is a human-typed slug (used on the CLI and in routing_profiles.yaml)."""

    __tablename__ = "model_registry"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    display_name: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(
        Text
    )  # ollama_library | huggingface_gguf | huggingface_mlx | hosted
    repo_id: Mapped[str] = mapped_column(Text)
    file_or_tag: Mapped[str | None] = mapped_column(Text)
    runtime: Mapped[str] = mapped_column(Text)  # ollama | mlx | hosted
    role: Mapped[str] = mapped_column(Text)  # chat | code | embed | rerank | stt | tts | judge
    quant: Mapped[str | None] = mapped_column(Text)
    size_gb: Mapped[float | None] = mapped_column(Float)
    context_len: Mapped[int | None] = mapped_column(Integer)
    licence: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        Text, default="available"
    )  # available|downloading|ready|failed|removed
    benchmark_json: Mapped[JsonDict | None] = mapped_column(JSON)
    price_in_per_mtok: Mapped[float] = mapped_column(Float, default=0.0)
    price_out_per_mtok: Mapped[float] = mapped_column(Float, default=0.0)
    local_path: Mapped[str | None] = mapped_column(Text)
    added_at: Mapped[str] = mapped_column(Text, default=utcnow_iso)
    updated_at: Mapped[str] = mapped_column(Text, default=utcnow_iso, onupdate=utcnow_iso)


# ---------------------------------------------------------------- UX
class ParkingLotItem(IdMixin, LearnerScoped, Base):
    __tablename__ = "parking_lot_item"
    session_id: Mapped[str | None] = mapped_column(Text, ForeignKey("session.id"))
    text: Mapped[str] = mapped_column(Text)
    node_id: Mapped[str | None] = mapped_column(Text, ForeignKey("skill_node.id"))
    status: Mapped[str] = mapped_column(Text, default="parked")  # parked | promoted | dropped
    promoted_to: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, default=utcnow_iso)


class Adaptation(IdMixin, LearnerScoped, Base):
    __tablename__ = "adaptation"
    what: Mapped[str] = mapped_column(Text)
    why: Mapped[str] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(Text)  # observed_pattern | planner | learner
    policy_version: Mapped[str] = mapped_column(Text, default="v1")
    reversible: Mapped[bool] = mapped_column(Boolean, default=True)
    proposed_at: Mapped[str] = mapped_column(Text, default=utcnow_iso)
    pattern: Mapped[str] = mapped_column(Text, default="")  # rule id (kernel/adaptation.py)
    apply_json: Mapped[JsonDict] = mapped_column(JSON, default=dict)  # {"pref": key, "value": v}
    previous_json: Mapped[JsonDict | None] = mapped_column(JSON)  # value before it was applied
    evidence_json: Mapped[JsonDict] = mapped_column(JSON, default=dict)  # the observed numbers
    session_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("session.id", name="fk_adaptation_session"), index=True
    )  # trial scope


class AdaptationDecision(IdMixin, LearnerScoped, Base):
    __tablename__ = "adaptation_decision"
    adaptation_id: Mapped[str] = mapped_column(Text, ForeignKey("adaptation.id"), index=True)
    decision: Mapped[str] = mapped_column(Text)  # try | default | no | never
    decided_at: Mapped[str] = mapped_column(Text, default=utcnow_iso)
    undone_at: Mapped[str | None] = mapped_column(Text)


class Experiment(IdMixin, LearnerScoped, Base):
    __tablename__ = "experiment"
    name: Mapped[str] = mapped_column(Text)
    hypothesis: Mapped[str] = mapped_column(Text, default="")
    metric: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="draft")  # draft | running | done
    created_at: Mapped[str] = mapped_column(Text, default=utcnow_iso)
    unit_type: Mapped[str] = mapped_column(Text, default="node")  # node (matched) | session
    started_at: Mapped[str | None] = mapped_column(Text)
    ended_at: Mapped[str | None] = mapped_column(Text)


class ExperimentArm(IdMixin, Base):
    __tablename__ = "experiment_arm"
    experiment_id: Mapped[str] = mapped_column(Text, ForeignKey("experiment.id"), index=True)
    name: Mapped[str] = mapped_column(Text)
    config_json: Mapped[JsonDict] = mapped_column(JSON, default=dict)


class ExperimentAssignment(IdMixin, LearnerScoped, Base):
    """Which arm a unit (session or skill node) got; balanced, deterministic, logged as `assigned`."""

    __tablename__ = "experiment_assignment"
    __table_args__ = (UniqueConstraint("experiment_id", "unit_id", name="uq_assignment_unit"),)
    experiment_id: Mapped[str] = mapped_column(
        Text, ForeignKey("experiment.id", name="fk_assignment_experiment"), index=True
    )
    arm_id: Mapped[str] = mapped_column(
        Text, ForeignKey("experiment_arm.id", name="fk_assignment_arm")
    )
    unit_type: Mapped[str] = mapped_column(Text)  # session | node
    unit_id: Mapped[str] = mapped_column(Text, index=True)
    ts: Mapped[str] = mapped_column(Text, default=utcnow_iso)


class ExperimentObservation(IdMixin, LearnerScoped, Base):
    __tablename__ = "experiment_observation"
    experiment_id: Mapped[str] = mapped_column(Text, ForeignKey("experiment.id"), index=True)
    arm_id: Mapped[str] = mapped_column(Text, ForeignKey("experiment_arm.id"))
    metric: Mapped[str] = mapped_column(Text)
    value: Mapped[float] = mapped_column(Float)
    n: Mapped[int] = mapped_column(Integer, default=1)
    ts: Mapped[str] = mapped_column(Text, default=utcnow_iso)


# ---------------------------------------------------------------- observability
class ModelCall(IdMixin, Base):
    __tablename__ = "model_call"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_model_call_idempotency_key"),)
    learner_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("learner_profile.id"), index=True
    )
    session_id: Mapped[str | None] = mapped_column(Text, ForeignKey("session.id"), index=True)
    ts: Mapped[str] = mapped_column(Text, default=utcnow_iso, index=True)
    provider: Mapped[str] = mapped_column(Text)  # ollama | mlx | anthropic | fake
    model: Mapped[str] = mapped_column(Text)
    registry_id: Mapped[str] = mapped_column(Text, index=True)
    task: Mapped[str] = mapped_column(Text, index=True)
    route: Mapped[str] = mapped_column(Text, default="primary")  # primary | fallback | degraded
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    cached_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    cached: Mapped[bool] = mapped_column(Boolean, default=False)
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    error: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[JsonDict] = mapped_column(JSON, default=dict)
    # P6 usage accounting. One gateway call = one request_id; every provider attempt (fallback,
    # structured-output repair) is its own row with attempt 1..n and a unique idempotency key.
    request_id: Mapped[str | None] = mapped_column(Text, index=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    idempotency_key: Mapped[str | None] = mapped_column(Text)
    # ok | error | invalid_output | cancelled | partial | blocked
    outcome: Mapped[str] = mapped_column(Text, default="ok")
    # reported (provider usage) | estimated (chars/4 or partial) | unavailable | legacy (pre-P6 row)
    usage_source: Mapped[str] = mapped_column(Text, default="legacy")
    # free (local) | reported (provider price) | estimated (tokens × registry price) | unknown
    # (failed hosted call, billing unknown — counted at reserved_usd) | legacy (pre-P6 row)
    cost_status: Mapped[str] = mapped_column(Text, default="legacy")
    reserved_usd: Mapped[float] = mapped_column(Float, default=0.0)


class BudgetReservation(IdMixin, Base):
    """P6: a hosted call reserves its worst-case cost before it runs (prompt estimate + max_tokens
    at the registry price) so concurrent calls cannot overshoot the daily cap; it is reconciled to
    the real/estimated cost afterwards, released when the provider was never reached, or expires
    (stale) after RESERVATION_TTL. `open` reservations count toward the cap."""

    __tablename__ = "budget_reservation"
    learner_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("learner_profile.id"), index=True
    )
    request_id: Mapped[str] = mapped_column(Text, index=True)
    registry_id: Mapped[str] = mapped_column(Text)
    task: Mapped[str] = mapped_column(Text)
    amount_usd: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(Text, default="open")  # open|reconciled|released|expired
    settled_usd: Mapped[float | None] = mapped_column(Float)
    model_call_id: Mapped[str | None] = mapped_column(Text, ForeignKey("model_call.id"))
    created_at: Mapped[str] = mapped_column(Text, default=utcnow_iso, index=True)
    expires_at: Mapped[str] = mapped_column(Text, index=True)


class RetrievalTrace(IdMixin, Base):
    __tablename__ = "retrieval_trace"
    learner_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("learner_profile.id"), index=True
    )
    session_id: Mapped[str | None] = mapped_column(Text, ForeignKey("session.id"), index=True)
    ts: Mapped[str] = mapped_column(Text, default=utcnow_iso)
    collection: Mapped[str] = mapped_column(Text)
    query: Mapped[str] = mapped_column(Text)
    filters_json: Mapped[JsonDict] = mapped_column(JSON, default=dict)
    bm25_scores_json: Mapped[JsonDict] = mapped_column(JSON, default=dict)
    vector_scores_json: Mapped[JsonDict] = mapped_column(JSON, default=dict)
    fused_json: Mapped[JsonDict] = mapped_column(JSON, default=dict)
    reranked_json: Mapped[JsonDict | None] = mapped_column(JSON)
    reranker_id: Mapped[str | None] = mapped_column(Text)  # registry id of the cross-encoder
    chunk_ids_json: Mapped[JsonList] = mapped_column(JSON, default=list)
    flagged_patterns_json: Mapped[JsonList] = mapped_column(JSON, default=list)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)


class TutorTrace(IdMixin, LearnerScoped, Base):
    __tablename__ = "tutor_trace"
    session_id: Mapped[str] = mapped_column(Text, ForeignKey("session.id"), index=True)
    turn_id: Mapped[str] = mapped_column(Text, index=True)
    ts: Mapped[str] = mapped_column(Text, default=utcnow_iso)
    action: Mapped[str] = mapped_column(Text)  # explain | hint | assess | quiz | summarize
    prompt_version: Mapped[str] = mapped_column(Text)
    sections_json: Mapped[JsonDict] = mapped_column(JSON, default=dict)  # section -> tokens used
    dropped_json: Mapped[JsonList] = mapped_column(JSON, default=list)  # what the budget cut
    model_call_id: Mapped[str | None] = mapped_column(Text, ForeignKey("model_call.id"))
    retrieval_trace_id: Mapped[str | None] = mapped_column(Text, ForeignKey("retrieval_trace.id"))
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)


class LearningEvent(IdMixin, LearnerScoped, Base):
    """Append-only. Envelope per docs/EVENT-SCHEMA.md; guarded by triggers in app.db.ddl."""

    __tablename__ = "learning_event"
    ts: Mapped[str] = mapped_column(Text, default=utcnow_iso, index=True)
    session_id: Mapped[str | None] = mapped_column(Text, ForeignKey("session.id"), index=True)
    actor: Mapped[str] = mapped_column(Text)  # learner | system | tutor
    verb: Mapped[str] = mapped_column(Text, index=True)
    object_type: Mapped[str] = mapped_column(Text)
    object_id: Mapped[str] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(Text)
    activity_type: Mapped[str] = mapped_column(Text)
    representation: Mapped[str | None] = mapped_column(Text)
    modality: Mapped[str] = mapped_column(Text, default="text")
    mode: Mapped[str] = mapped_column(Text)
    energy: Mapped[int] = mapped_column(Integer)
    socratic: Mapped[bool] = mapped_column(Boolean, default=False)
    experiment_arm: Mapped[str | None] = mapped_column(Text)
    result_json: Mapped[JsonDict | None] = mapped_column(JSON)
    context_json: Mapped[JsonDict | None] = mapped_column(JSON)


Index("ix_learning_event_session_verb", LearningEvent.session_id, LearningEvent.verb)

for _ddl in LEARNING_EVENT_GUARDS.values():
    event.listen(LearningEvent.__table__, "after_create", DDL(_ddl))  # type: ignore[no-untyped-call]


def learner_scoped_tables() -> list[str]:
    """Names of every table that carries a learner_id column (used by export/wipe)."""
    return [t.name for t in Base.metadata.sorted_tables if "learner_id" in t.c]


class CurriculumDraft(IdMixin, LearnerScoped, Base):
    """P4: a reviewable course→curriculum proposal (skills, prerequisites, learning objects,
    assessments) linked to source chunks. `draft` → `published` (applied to skill_node /
    learning_object / assessment with versioning) or `rejected`. Publishing never edits history:
    a re-publish writes a new learning_object version and new assessment rows."""

    __tablename__ = "curriculum_draft"
    course: Mapped[str] = mapped_column(Text, index=True)
    section: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        Text, default="draft", index=True
    )  # draft|published|rejected
    origin: Mapped[str] = mapped_column(Text, default="deterministic")  # deterministic | model
    payload_json: Mapped[JsonDict] = mapped_column(JSON, default=dict)
    validation_json: Mapped[JsonList] = mapped_column(JSON, default=list)  # problems found
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str] = mapped_column(Text, default=utcnow_iso)
    updated_at: Mapped[str] = mapped_column(Text, default=utcnow_iso, onupdate=utcnow_iso)
    published_at: Mapped[str | None] = mapped_column(Text)
    model_call_id: Mapped[str | None] = mapped_column(Text)  # when a model drafted it


class IngestRun(IdMixin, Base):
    """Course-material stage 1: one ingest run (CLI or API job). Not learner state — the corpus is
    shared — but the record makes a long run explainable while it runs and resumable after an
    interruption: items already recorded with a terminal outcome are not processed again."""

    __tablename__ = "ingest_run"
    src: Mapped[str] = mapped_column(Text, index=True)  # resolved path the run walked
    course: Mapped[str | None] = mapped_column(Text)
    options_json: Mapped[JsonDict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(Text, default="running", index=True)
    # running | finished | interrupted | failed
    started_at: Mapped[str] = mapped_column(Text, default=utcnow_iso)
    finished_at: Mapped[str | None] = mapped_column(Text)
    files_total: Mapped[int] = mapped_column(Integer, default=0)
    files_done: Mapped[int] = mapped_column(Integer, default=0)
    last_uri: Mapped[str | None] = mapped_column(Text)
    resumed_from: Mapped[str | None] = mapped_column(Text, ForeignKey("ingest_run.id"))
    summary_json: Mapped[JsonDict] = mapped_column(JSON, default=dict)


class IngestRunItem(IdMixin, Base):
    """One terminal outcome per file or archive member of a run (imported, unchanged,
    reference_only, no_content, unsupported, gated, retryable_error, access_blocked,
    parser_error) — the audit trail behind the progress counts and the resume set."""

    __tablename__ = "ingest_run_item"
    __table_args__ = (UniqueConstraint("run_id", "uri", name="uq_ingest_run_item_run_uri"),)
    run_id: Mapped[str] = mapped_column(Text, ForeignKey("ingest_run.id"), index=True)
    uri: Mapped[str] = mapped_column(Text)
    outcome: Mapped[str] = mapped_column(Text, index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    document_id: Mapped[str | None] = mapped_column(Text)
    version_id: Mapped[str | None] = mapped_column(Text)
    ts: Mapped[str] = mapped_column(Text, default=utcnow_iso)


class ContentReport(IdMixin, LearnerScoped, Base):
    """P4: 'this source / explanation is wrong' — kept as a report next to the evidence, never a
    silent rewrite of what the learner saw."""

    __tablename__ = "content_report"
    kind: Mapped[str] = mapped_column(
        Text
    )  # wrong_source | wrong_explanation | wrong_grading | other
    turn_id: Mapped[str | None] = mapped_column(Text, index=True)
    chunk_id: Mapped[str | None] = mapped_column(Text, index=True)
    skill_id: Mapped[str | None] = mapped_column(Text, index=True)
    assessment_id: Mapped[str | None] = mapped_column(Text, index=True)  # P7: a wrong item
    note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(Text, default="open")  # open | resolved
    created_at: Mapped[str] = mapped_column(Text, default=utcnow_iso)
