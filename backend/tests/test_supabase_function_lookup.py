import pytest
from pydantic import ValidationError

from app.integrations.supabase_function_lookup import (
    EvidenceCheck,
    FunctionChoice,
    Requirement,
    cited_hit,
    requested_chapter,
)


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Which PostgreSQL hstore function returns all keys?", "hstore"),
        ("Welche PostgreSQL-ltree-Funktion zählt alle Labels?", "ltree"),
        ("Which pageinspect function returns items? Can you repair it?", None),
        ("Which function should I use?", None),
    ],
)
def test_question_scope(question, expected):
    assert requested_chapter(question) == expected


@pytest.mark.parametrize(
    ("address", "tier", "identifier", "quote", "expected"),
    [
        (
            "https://www.postgresql.org/docs/17/ltree.html#functions",
            2,
            "nlevel",
            "nlevel counts labels",
            True,
        ),
        (
            "https://www.postgresql.org/docs/18/ltree.html",
            2,
            "nlevel",
            "nlevel counts labels",
            False,
        ),
        (
            "https://www.postgresql.org/docs/17/hstore.html",
            2,
            "nlevel",
            "nlevel counts labels",
            False,
        ),
        (
            "https://www.postgresql.org.example/docs/17/ltree.html",
            2,
            "nlevel",
            "nlevel counts labels",
            False,
        ),
        (
            "https://www.postgresql.org/docs/17/ltree.html",
            1,
            "nlevel",
            "nlevel counts labels",
            False,
        ),
        (
            "https://www.postgresql.org/docs/17/ltree.html",
            2,
            "level",
            "nlevel counts labels",
            False,
        ),
        (
            "https://www.postgresql.org/docs/17/ltree.html",
            2,
            "nlevel",
            "nlevel counts tables",
            False,
        ),
    ],
)
def test_hit_requires_matching_page_and_literal_evidence(
    address, tier, identifier, quote, expected
):
    choice = FunctionChoice(identifier=identifier, passage=1, support=quote)
    hits = [dict(url=address, tier=tier, content="nlevel counts labels")]
    assert (cited_hit(choice, hits, "ltree") is not None) == expected
    assert cited_hit(choice, [], "ltree") is None


def test_every_requirement_needs_verbatim_evidence():
    supported = Requirement(requirement="count labels", supported=True, words="counts labels")
    assert EvidenceCheck(requirements=[supported]).supports("nlevel counts labels")
    for invalid in [
        Requirement(requirement="unique path", supported=False, words="counts labels"),
        Requirement(requirement="count labels", supported=True, words="counts unique labels"),
        Requirement(requirement="count labels", supported=True, words=" "),
    ]:
        assert not EvidenceCheck(requirements=[supported, invalid]).supports("nlevel counts labels")
    with pytest.raises(ValidationError):
        EvidenceCheck(requirements=[])
