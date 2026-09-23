"""The tutor's retrieval widens step by step: skill → the skill's course → the whole corpus. A
lesson published from a course is taught from that course; another course's notebooks are only
consulted when the course itself has nothing (found by the first live rehearsal, 2026-09-23)."""

from app.knowledge.provenance import Provenance, TrustTier
from app.knowledge.repository import ChunkRecord
from app.knowledge.sqlite_hybrid import SqliteHybridRepository
from app.orchestrator import tools


def _chunk(i: str, text: str, course: str, skills: list[str] | None = None) -> ChunkRecord:
    return ChunkRecord(
        id=i,
        text=text,
        skill_ids=skills or [],
        provenance=Provenance(
            source_id=f"src-{course}",
            path=f"{course}/{i}.ipynb",
            source_type="notebook",
            trust_tier=TrustTier.COURSE,
            course=course,
            section="1",
            lecture=i,
        ),
    )


async def test_retrieval_widens_to_the_course_before_the_corpus(
    fake_repo: SqliteHybridRepository,
) -> None:
    await fake_repo.upsert(
        [
            _chunk(
                "a-skill", "pipeline function loads a pretrained model for sentiment", "A", ["s1"]
            ),
            _chunk(
                "a-1", "the pipeline function wraps tokenizer and model for sentiment analysis", "A"
            ),
            _chunk(
                "a-2",
                "sentiment analysis with a pipeline: pretrained model, tokenizer, labels",
                "A",
            ),
            _chunk("b-1", "pipeline function sentiment analysis pretrained model tokenizer", "B"),
            _chunk(
                "b-2", "sentiment pipeline pretrained model loads labels tokenizer function", "B"
            ),
        ]
    )
    query = "pipeline function sentiment pretrained model"
    # one skill-tagged hit is too little: widen to course A, never to course B
    res = await tools.retrieve(fake_repo, query, skill_id="s1", course="A", k=6)
    courses = {h.chunk.provenance.course for h in res.hits}
    assert courses == {"A"}, [h.chunk.id for h in res.hits]
    assert res.hits[0].chunk.id == "a-skill" and len(res.hits) >= 2
    assert res.trace.filters["widened"] == ["course"] and res.trace.filters["course"] == "A"
    # a course without material of its own falls through to the corpus, and says so
    res = await tools.retrieve(fake_repo, query, skill_id="s1", course="Z", k=6)
    assert res.trace.filters["widened"] == ["course", "corpus"]
    assert {h.chunk.provenance.course for h in res.hits} >= {"A", "B"}
    # no course known (seed skills): the old behaviour, straight to the corpus
    res = await tools.retrieve(fake_repo, query, skill_id="s1", course=None, k=6)
    assert res.trace.filters["widened"] == ["corpus"]
    # enough skill-tagged material: no widening at all
    await fake_repo.upsert(
        [_chunk("a-skill-2", "pipeline sentiment model second passage", "A", ["s1"])]
    )
    res = await tools.retrieve(fake_repo, query, skill_id="s1", course="A", k=6)
    assert "widened" not in res.trace.filters and {h.chunk.id for h in res.hits} == {
        "a-skill",
        "a-skill-2",
    }
