"""retrieval-evals slice: label matching, metrics, report, baseline deltas, label integrity."""

from pathlib import Path

from app.db.traces import RetrievalTraceRecord
from app.evals.retrieval import (
    Expected,
    LabelledQuery,
    compare,
    evaluate,
    has_citation,
    load_queries,
    percentile,
    score_query,
)
from app.knowledge.ingest.loaders import iter_source_files, load_file
from app.knowledge.provenance import Provenance
from app.knowledge.repository import ChunkRecord, ScoredChunk, SearchFilters, SearchResult

ROOT = Path(__file__).resolve().parents[2]
QUERIES = ROOT / "evals" / "retrieval" / "queries.yaml"
COURSES = ROOT / "seeds" / "courses"


def _hit(rank: int, course: str, lecture: str, text: str, trust: int = 2) -> ScoredChunk:
    return ScoredChunk(
        chunk=ChunkRecord(
            id=f"{course}-{lecture}-{rank}",
            text=text,
            provenance=Provenance(
                source_id="s",
                path="p",
                source_type="udemy_caption",
                course=course,
                lecture=lecture,
                trust_tier=trust,
            ),
        ),
        score=1.0 / (rank + 1),
        rank=rank,
    )


def test_expected_matches_normalised_labels_and_phrases() -> None:
    hit = _hit(0, "LLM Evaluation", "Perplexity", "Perplexity is the exponential of the NLL.")
    assert Expected(course="llm evaluation", lecture="PERPLEXITY").matches(hit)
    assert Expected(lecture="Perplexity", contains="exponential of the nll").matches(hit)
    assert not Expected(lecture="Perplexity", contains="tokeniser").matches(hit)
    assert not Expected(course="Other").matches(hit)
    assert has_citation(hit) and not has_citation(_hit(0, "Forum", "x", "t", trust=0))


def test_score_query_recall_and_reciprocal_rank() -> None:
    q = LabelledQuery(
        id="q",
        query="x",
        expected=[Expected(lecture="A"), Expected(lecture="B", contains="beta")],
    )
    hits = [_hit(0, "C", "Z", "zzz"), _hit(1, "C", "A", "aaa"), _hit(2, "C", "B", "no phrase")]
    recall, rr, found = score_query(q, hits)
    assert recall == 0.5 and rr == 0.5 and found == [True, False]
    assert score_query(q, [])[0] == 0.0
    assert percentile([5, 1, 9, 3], 0.5) == 5 and percentile([5, 1, 9, 3], 0.95) == 9


class CannedRepo:
    collection = "canned"

    def __init__(self, answers: dict[str, list[ScoredChunk]]) -> None:
        self.answers = answers
        self.filters: list[SearchFilters | None] = []

    async def search(
        self, query: str, filters: SearchFilters | None = None, k: int = 8
    ) -> SearchResult:
        self.filters.append(filters)
        hits = self.answers.get(query, [])[:k]
        return SearchResult(
            hits=hits, trace=RetrievalTraceRecord(collection=self.collection, query=query)
        )

    async def upsert(self, chunks: list[ChunkRecord]) -> int:
        return 0

    async def delete(self, ids: list[str]) -> None:
        return None

    async def count(self) -> int:
        return 0

    async def reindex(self, chunks: list[ChunkRecord]) -> int:
        return 0


async def test_evaluate_builds_report_and_compare_deltas() -> None:
    queries = [
        LabelledQuery(id="a", query="qa", expected=[Expected(lecture="A")]),
        LabelledQuery(
            id="b", query="qb", expected=[Expected(lecture="B")], filters={"course": "C"}
        ),
        LabelledQuery(id="c", query="qc", expected=[Expected(lecture="C")]),
    ]
    repo = CannedRepo(
        {
            "qa": [_hit(0, "C", "A", "a")],
            "qb": [_hit(0, "C", "X", "x"), _hit(1, "C", "B", "b", trust=0)],
            "qc": [_hit(0, "C", "X", "x")],
        }
    )
    report = await evaluate(repo, queries, k=8)
    assert report.queries == 3 and report.misses == ["c"]
    assert report.recall_at_k == round(2 / 3, 4) and report.mrr == round((1 + 0.5) / 3, 4)
    assert report.recall_at_1 == round(1 / 3, 4) and report.recall_at_4 == report.recall_at_k
    assert report.citation_coverage == round((1 + 0.5 + 1) / 3, 4)  # trust-0 hit is not citable
    assert repo.filters[1] == SearchFilters(course="C") and report.results[1].found == [True]
    assert "summary" not in report.summary() and "results" not in report.summary()
    deltas = compare(report, {"recall_at_k": 0.5, "mrr": 0.5, "citation_coverage": 1.0})
    assert deltas["recall_at_k"] == round(2 / 3 - 0.5, 4) and deltas["citation_coverage"] < 0
    assert compare(report, None) == {}


def test_labelled_queries_point_at_real_lectures() -> None:
    """Every label must resolve to a (course, lecture) that the sample courses actually contain,
    and every `contains` phrase must occur in that lecture — otherwise the eval measures typos."""
    queries = load_queries(QUERIES)
    assert len(queries) >= 30 and len({q.id for q in queries}) == len(queries)
    lectures: dict[tuple[str, str], str] = {}
    for p in iter_source_files(COURSES):
        doc = load_file(p, root=COURSES)
        assert doc.course and doc.lecture
        lectures[(doc.course.casefold(), doc.lecture.casefold())] = doc.text.casefold()
    for q in queries:
        for e in q.expected:
            assert e.course and e.lecture, q.id
            key = (e.course.casefold(), e.lecture.casefold())
            assert key in lectures, f"{q.id}: unknown lecture {key}"
            if e.contains:
                assert e.contains.casefold() in lectures[key], f"{q.id}: phrase not in lecture"
