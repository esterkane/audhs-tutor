import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import event_queries, models
from app.db.events import EventContext, EventPayloadError, EventWriter, Verb
from app.db.traces import (
    ModelCallRecord,
    RetrievalTraceRecord,
    TutorTraceRecord,
    write_model_call,
    write_retrieval_trace,
    write_tutor_trace,
)
from app.schemas.common import Mode, ObjectType


async def _session(db: AsyncSession, learner: models.LearnerProfile) -> models.Session:
    s = models.Session(learner_id=learner.id, mode="steady", energy=3)
    db.add(s)
    await db.commit()
    return s


async def test_emit_stamps_context_and_validates(
    db: AsyncSession, learner: models.LearnerProfile
) -> None:
    s = await _session(db, learner)
    w = EventWriter(db, EventContext(learner.id, s.id, Mode.NOVELTY, energy=4, socratic=True))
    ev = await w.emit(
        Verb.EXPLAINED,
        ObjectType.TURN,
        "t1",
        result={"sentences": 3, "cited_sources": ["c1"]},
        context={"representation": "analogy", "hint_count": 0, "model": "m", "route": "local"},
        representation="analogy",
    )
    assert ev.mode == "novelty" and ev.energy == 4 and ev.socratic is True
    assert ev.learner_id == learner.id and ev.session_id == s.id
    assert len(ev.id) == 26 and ev.ts.endswith("+00:00")

    with pytest.raises(EventPayloadError, match="undocumented result keys \\['mood'\\]"):
        await w.emit(Verb.ASKED, ObjectType.TURN, "t2", result={"mood": "?"})

    rows = await event_queries.events_for_session(db, s.id)
    assert [r.verb for r in rows] == ["explained"]
    assert await event_queries.count_by_verb(db, learner.id) == {"explained": 1}
    assert (await event_queries.last_event(db, learner.id, "explained")) is not None


def test_every_verb_has_payload_rules() -> None:
    from app.db.events import PAYLOAD_KEYS

    assert set(PAYLOAD_KEYS) == set(Verb)


async def test_trace_writers_and_spend(db: AsyncSession, learner: models.LearnerProfile) -> None:
    s = await _session(db, learner)
    mc = await write_model_call(
        db,
        ModelCallRecord(
            provider="anthropic",
            model="claude-sonnet-5",
            registry_id="hosted-medium",
            task="grade_rubric",
            tokens_in=100,
            tokens_out=50,
            cost_usd=0.0007,
            latency_ms=900,
            learner_id=learner.id,
            session_id=s.id,
        ),
    )
    await write_model_call(
        db,
        ModelCallRecord(
            provider="ollama", model="llama3.1:8b", registry_id="llama31-8b", task="chat"
        ),
    )
    rt = await write_retrieval_trace(
        db,
        RetrievalTraceRecord(
            collection="corpus_v1",
            query="what is attention",
            fused={"c1": 0.9},
            chunk_ids=["c1"],
            flagged_patterns=["ignore previous instructions"],
            learner_id=learner.id,
        ),
    )
    tt = await write_tutor_trace(
        db,
        TutorTraceRecord(
            learner_id=learner.id,
            session_id=s.id,
            turn_id="t1",
            action="explain",
            prompt_version="pedagogy.v1",
            sections={"policy": 400, "retrieved": 1200},
            dropped=["evidence:misconceptions"],
            model_call_id=mc.id,
            retrieval_trace_id=rt.id,
        ),
    )
    assert tt.model_call_id == mc.id and tt.retrieval_trace_id == rt.id
    from app.models_ai.budget import Budget

    # a hosted row written without an explicit status is priced by tokens → "estimated", counted
    assert (await Budget(1.0).spend_today(db)).estimated == pytest.approx(0.0007)
