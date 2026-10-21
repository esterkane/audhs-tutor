import statistics

import pytest
from pydantic import ValidationError

from app.schemas.knowledge_authoring import (
    ResearchDiscussion,
    ResearchSectionDraft,
    ResearchTutorAnswer,
)


@pytest.mark.parametrize(
    "schema,key", [(ResearchDiscussion, "answer_sentence"), (ResearchSectionDraft, "section")]
)
@pytest.mark.parametrize(
    "claim",
    [
        "The median averages the middle values to maintain symmetry.",
        "The median averages the central observations to balance the distribution.",
        "The median averages two central values to balance opposing halves.",
        "The median represents central tendency by balancing the distribution.",
        "The median uses the mean because averaging balances the distribution.",
    ],
)
def test_fresh_median_explanations_reject_observed_invented_purposes(schema, key, claim):
    with pytest.raises(ValidationError, match="middle ranks"):
        schema.model_validate({key: claim, "source_indices": [1]})


@pytest.mark.parametrize(
    "claim",
    [
        "The median is 8: (6 + 10) / 2. The odd-sized dataset has median 9.",
        "The median does not make data symmetric or balance its distribution.",
        "The median is not calculated to maintain symmetry.",
        "The source discusses symmetry, but the median uses the middle ranks.",
    ],
)
def test_preserves_calculations_and_negated_corrections(claim):
    assert ResearchDiscussion(answer_sentence=claim, source_indices=[1]).answer_sentence == claim


def test_asymmetric_data_still_use_even_median_convention():
    data = [0, 1, 3, 100]
    assert statistics.median(data) == 2
    assert [2 - value for value in data[:2]] != [value - 2 for value in reversed(data[2:])]


def test_historical_public_answer_remains_readable_without_rewriting():
    original = "The median averages two values to balance the distribution."
    assert ResearchTutorAnswer(discussion=original).discussion == original
