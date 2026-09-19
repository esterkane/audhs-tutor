from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.db.events import EventWriter
from app.kernel import competency, memory, session, skill_graph
from app.kernel.seed import load_seed
from app.knowledge.ingest.markdown import chunk_sections, parse_markdown
from app.schemas.common import Mode

SEED = Path(__file__).resolve().parents[2] / "seeds" / "attention"
NOW = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)


@pytest.fixture
async def seeded(db: AsyncSession) -> AsyncSession:
    rep = await load_seed(db, SEED)
    assert rep.skills == 8 and rep.learning_objects == 8 and rep.assessments == 18
    return db


def test_markdown_parser_and_chunks() -> None:
    doc = parse_markdown((SEED / "sources" / "attention-study-notes.md").read_text())
    assert doc.title.startswith("Attention Mechanisms")
    assert [s.skill_slugs for s in doc.sections][:3] == [
        ["vec-dot-product"],
        ["softmax"],
        ["attn-dot-product"],
    ]
    chunks = chunk_sections(doc, max_chars=600)
    assert len(chunks) >= len(doc.sections)
    assert chunks[0].text.startswith(
        "Attention Mechanisms — Study Notes › Dot product as similarity"
    )
    assert all(len(c.text) < 1400 for c in chunks)


async def test_seed_is_idempotent_and_tags_chunks(seeded: AsyncSession) -> None:
    again = await load_seed(seeded, SEED)
    assert again.skills == 8 and all(not d["changed"] for d in again.documents)
    nodes = await skill_graph.all_nodes(seeded)
    assert len(nodes) == 8 and len(await skill_graph.all_edges(seeded)) == 8
    assert len((await seeded.execute(select(models.Assessment))).scalars().all()) == 18
    docs = (await seeded.execute(select(models.Document))).scalars().all()
    assert len(docs) == 2
    kv = await skill_graph.get_node_by_slug(seeded, "kv-cache")
    assert kv is not None
    chunks = (await seeded.execute(select(models.Chunk))).scalars().all()
    tagged = [c for c in chunks if kv.id in c.skill_ids_json]
    assert len(tagged) >= 1 and "KV cache" in tagged[0].text
    prov = (await seeded.execute(select(models.ChunkProvenance))).scalars().all()
    assert len(prov) == len(chunks) and all(p.course == "Attention Mechanisms (seed)" for p in prov)


async def test_topological_order_and_next_skill(
    seeded: AsyncSession, learner: models.LearnerProfile
) -> None:
    order = [n.slug for n in await skill_graph.topological_order(seeded)]
    assert (
        order.index("vec-dot-product")
        < order.index("attn-dot-product")
        < order.index("attn-scaled")
    )
    assert order.index("attn-masking") < order.index("kv-cache")
    first = await skill_graph.next_skill(seeded, learner.id)
    assert first is not None and first.slug in {"vec-dot-product", "softmax"}  # both roots
    scaled = await skill_graph.get_node_by_slug(seeded, "attn-scaled")
    assert scaled is not None and not await skill_graph.is_unlocked(seeded, learner.id, scaled.id)


async def _learn(
    db: AsyncSession, learner_id: str, skill_id: str, scores: list[tuple[str, float]]
) -> float:
    for dim, score in scores:
        await competency.record_evidence(
            db, learner_id, skill_id, dim, score, grader_level="deterministic"
        )
    await competency.refresh(db, learner_id, skill_id, now=NOW)
    return await competency.mastery(db, learner_id, skill_id)


async def test_competency_refresh_mastery_and_unlock(
    seeded: AsyncSession, learner: models.LearnerProfile
) -> None:
    dot = await skill_graph.get_node_by_slug(seeded, "vec-dot-product")
    soft = await skill_graph.get_node_by_slug(seeded, "softmax")
    attn = await skill_graph.get_node_by_slug(seeded, "attn-dot-product")
    assert dot and soft and attn
    # one lucky MCQ: recall only, half coverage -> low mastery, nothing unlocks
    m1 = await _learn(seeded, learner.id, dot.id, [("recall", 1.0)])
    assert m1 == pytest.approx(0.25 * 1.0 * 0.5 / 0.6, abs=1e-3)
    assert not await skill_graph.is_unlocked(seeded, learner.id, attn.id)
    # two recall + one good explanation -> above unlock threshold
    m2 = await _learn(seeded, learner.id, dot.id, [("recall", 1.0), ("explanation", 0.9)])
    assert m2 > 0.6
    await _learn(
        seeded, learner.id, soft.id, [("recall", 1.0), ("recall", 1.0), ("explanation", 1.0)]
    )
    assert await skill_graph.is_unlocked(seeded, learner.id, attn.id)
    nxt = await skill_graph.next_skill(seeded, learner.id)
    assert nxt is not None and nxt.slug == "attn-dot-product"
    st = await competency.skill_state(seeded, learner.id, dot.id)
    assert (
        st["dimensions"]["recall"]["count"] == 2
        and 0 < st["dimensions"]["recall"]["confidence"] < 1
    )
    # refresh is idempotent
    before = {
        d: (s.score, s.count)
        for d, s in (await competency.states(seeded, learner.id, dot.id)).items()
    }
    await competency.refresh(seeded, learner.id, dot.id, now=NOW)
    after = {
        d: (s.score, s.count)
        for d, s in (await competency.states(seeded, learner.id, dot.id)).items()
    }
    assert before == after


async def test_time_decay_favors_recent_evidence(
    seeded: AsyncSession, learner: models.LearnerProfile
) -> None:
    dot = await skill_graph.get_node_by_slug(seeded, "vec-dot-product")
    assert dot
    old = await competency.record_evidence(
        seeded, learner.id, dot.id, "recall", 0.0, grader_level="deterministic"
    )
    old.ts = (NOW - timedelta(days=90)).isoformat()
    await seeded.commit()
    await competency.record_evidence(
        seeded, learner.id, dot.id, "recall", 1.0, grader_level="deterministic"
    )
    st = await competency.refresh(seeded, learner.id, dot.id, now=NOW)
    assert st["recall"].score > 0.85  # 90-day-old zero is down-weighted by 1/8


async def test_fsrs_memory_review_and_time_travel(
    seeded: AsyncSession, learner: models.LearnerProfile
) -> None:
    dot = await skill_graph.get_node_by_slug(seeded, "vec-dot-product")
    assert dot
    s = await session.start(seeded, learner.id, mode=Mode.STEADY, energy=3)
    events = EventWriter(seeded, session.event_context(s))
    item, ms = await memory.ensure_item(
        seeded, learner.id, dot.id, "mcq", {"ref": "a1", "q": "?"}, now=NOW
    )
    same, _ = await memory.ensure_item(seeded, learner.id, dot.id, "mcq", {"ref": "a1"}, now=NOW)
    assert same.id == item.id and ms.state == "new"
    assert [i.id for i, _ in await memory.due_items(seeded, learner.id, now=NOW)] == [item.id]

    log = await memory.review(
        seeded, learner.id, item.id, 3, now=NOW, latency_ms=1200, events=events
    )
    assert log.rating == 3 and log.predicted_retrievability is not None
    ms = (await seeded.execute(select(models.MemoryState))).scalar_one()
    assert (
        ms.state in ("learning", "review") and ms.stability is not None and ms.due > NOW.isoformat()
    )
    # not due right now, due after two days
    assert await memory.due_items(seeded, learner.id, now=NOW) == []
    later = NOW + timedelta(days=2)
    assert len(await memory.due_items(seeded, learner.id, now=later)) == 1
    r = await memory.mean_retrievability(seeded, learner.id, dot.id, now=later)
    assert r is not None and 0.5 < r < 1.0
    # second review two days later -> stability grows, event logged
    stability_first = ms.stability
    await memory.review(seeded, learner.id, item.id, 3, now=later, events=events)
    ms2 = (await seeded.execute(select(models.MemoryState))).scalar_one()
    assert ms2.stability is not None and stability_first is not None
    assert ms2.stability > stability_first
    verbs = [e.verb for e in (await seeded.execute(select(models.LearningEvent))).scalars()]
    assert verbs.count("reviewed") == 2 and "started" in verbs
    # recall dimension blends retrievability into competency even with no evidence rows
    st = await competency.refresh(seeded, learner.id, dot.id, now=later)
    assert "recall" in st and st["recall"].count == 0 and st["recall"].score > 0.5


def test_review_cap_and_rating_rules() -> None:
    assert memory.review_cap("low_capacity", 5) == 5
    assert memory.review_cap("novelty", 5) == 15 and memory.review_cap("novelty", 2) == 5
    assert memory.review_cap("steady", 3) == 10
    assert int(memory.rating_from_score(0.2)) == 1 and int(memory.rating_from_score(1.0)) == 4
    assert (
        int(memory.rating_from_score(1.0, hint_count=1)) == 3
        and int(memory.rating_from_score(0.7)) == 2
    )


async def test_session_lifecycle_and_checkpoint(
    db: AsyncSession, learner: models.LearnerProfile
) -> None:
    s = await session.start(
        db, learner.id, mode=Mode.LOW_CAPACITY, energy=2, planned_blocks=["retrieval", "recap"]
    )
    await session.save_checkpoint(db, s, {"skill": "x", "turn": 1})
    assert await session.load_checkpoint(db, s.id) == {"skill": "x", "turn": 1}
    ended = await session.end(db, s.id, energy_after=3, self_report=4)
    assert ended.ended_at and ended.energy_after == 3
    verbs = [e.verb for e in (await db.execute(select(models.LearningEvent))).scalars()]
    assert verbs == ["started", "ended"]
    with pytest.raises(ValueError):
        await session.start(db, learner.id, mode=Mode.STEADY, energy=9)
